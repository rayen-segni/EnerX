from hiero_sdk_python.file.file_id import FileId
from hiero_sdk_python.file.file_contents_query import FileContentsQuery
from hiero_sdk_python.file.file_info_query import FileInfoQuery

from hedera.client import get_client

client = get_client()
file_id = FileId.from_string("0.0.10989080")

# Retrieve metadata
info = FileInfoQuery(file_id).execute(client)
print("File information:")
print(info)

# Retrieve contents
contents = FileContentsQuery(file_id).execute(client)

print("\nFile contents:")
if isinstance(contents, bytes):
    print(contents.decode("utf-8"))
else:
    print(contents)