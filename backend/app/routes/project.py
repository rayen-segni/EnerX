from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection

from app.config import settings
from app.database import get_db
from app.schemas.project import ProjectCreateRequest, ProjectCreateResponse, ProjectResponse
from hedera.file_service import create_project_commitment
from hedera.token_service import create_token

router = APIRouter(prefix="/project", tags=["Projects"])


@router.post("/", response_model=ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    request: ProjectCreateRequest,
    connection: Connection = Depends(get_db),
):

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT hedera_id FROM users WHERE id = %s",
            (request.user_id,),
        )
        user = cursor.fetchone()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} was not found",
            )

        # Insert the project into the database.
        cursor.execute(
            """
            INSERT INTO projects (owner_id, name, description, target_amount, status)
            VALUES (%s, %s, %s, %s, 'funding')
            RETURNING id, owner_id, name, description, target_amount, status
            """,
            (request.user_id, request.name, request.description, request.target_amount),
        )
        project = cursor.fetchone()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create project",
            )

        # Create the Hedera token for the project.
        try:
            token_creation = create_token(
                request.token_name,
                request.token_symbol,
                user["hedera_id"],  # type: ignore
            )
            hedera_token_id = token_creation["token_id"]
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not create Hedera token: {exc}",
            ) from exc

        # The HFS file is public and immutable; its equipment and owner
        # acknowledgement are explicitly simulated for this hackathon MVP.
        try:
            commitment = create_project_commitment(
                project_id=int(project["id"]),  # type: ignore[index]
                owner_user_id=request.user_id,
                owner_hedera_id=str(user["hedera_id"]),  # type: ignore[index]
                project_name=request.name,
                project_description=request.description,
                funding_target=request.target_amount,
                token_name=request.token_name,
                token_symbol=request.token_symbol,
                hedera_token_id=hedera_token_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Could not create the simulated Hedera File Service "
                    f"commitment: {exc}"
                ),
            ) from exc

        cursor.execute(
            """
            UPDATE projects
            SET commitment_file_id = %s,
                commitment_transaction_id = %s
            WHERE id = %s
            """,
            (
                commitment["file_id"],
                commitment["transaction_id"],
                project["id"],  # type: ignore[index]
            ),
        )

        # Insert the token into the database.
        cursor.execute(
            """
            INSERT INTO tokens (
                project_id,
                user_id,
                hedera_token_id,
                token_name,
                token_symbol,
                total_supply,
                initial_price
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                project["id"],  # type: ignore
                request.user_id,
                hedera_token_id,
                request.token_name,
                request.token_symbol,
                30,  # Initial supply of 30 tokens
                request.target_amount / 100,
            ),
        )
        token = cursor.fetchone()

        # Add the initial investment record.
        transaction_id = token_creation["transfer_transaction_id"] if token_creation else None
        cursor.execute(
            """
            INSERT INTO investments (project_id, investor_id, token_amount, amount_paid, transaction_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (project["id"], request.user_id, 30, 0, transaction_id), # type: ignore
        )
        
        #Update balance table
        cursor.execute(
            """
            INSERT INTO token_balances (token_id, user_id, amount)
            VALUES (%s, %s, %s)
            """,
            (token["id"], request.user_id, 30), # type: ignore
        )

    return {
        **project,  # type: ignore
        "token_id": token["id"] if token else None,  # type: ignore
        "hedera_token_id": hedera_token_id,
        "token_name": request.token_name,
        "token_symbol": request.token_symbol,
        "total_supply": 30,
        "commitment_file_id": commitment["file_id"],
        "commitment_transaction_id": commitment["transaction_id"],
    }

@router.get("/{owner_id}", response_model=list[ProjectResponse])
def get_project(
    owner_id: int,
    connection: Connection = Depends(get_db),
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                p.id,
                p.owner_id,
                p.name,
                p.description,
                t.token_name,
                t.token_symbol,
                t.id AS token_id,
                t.total_supply AS token_supply,
                p.commitment_file_id,
                p.commitment_transaction_id,
                p.target_amount,
                p.status
            FROM projects AS p
            JOIN tokens AS t ON t.project_id = p.id
            WHERE p.owner_id = %s
            ORDER BY p.id
            """,
            (owner_id,),
        )
        projects = cursor.fetchall()

    if not projects:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No projects found for owner {owner_id}",
        )

    return projects


@router.get("/", response_model=list[ProjectResponse])
def get_projects(connection: Connection = Depends(get_db)):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                p.id,
                p.owner_id,
                p.name,
                p.description,
                t.token_name,
                t.token_symbol,
                t.id AS token_id,
                t.total_supply AS token_supply,
                p.commitment_file_id,
                p.commitment_transaction_id,
                p.target_amount,
                p.status
            FROM projects AS p
            JOIN tokens AS t ON t.project_id = p.id
            ORDER BY p.id
            """
        )
        projects = cursor.fetchall()

    return projects