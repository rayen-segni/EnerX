// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title RevenueDistribution
 * @dev Hedera Smart Contract for EnerX Solar Project Revenue Distribution.
 * 
 * Main Responsibility:
 * Records and executes verifiable on-chain revenue distributions according to
 * current token ownership (total 100 tokens / 100%).
 * 
 * Hackathon MVP Architecture Rule:
 * General project CRUD, marketplace listings, and virtual balances remain in PostgreSQL.
 * The backend calculates current token ownership and submits the distribution snapshot
 * to this contract on Hedera Smart Contract Service (HSCS).
 */
contract RevenueDistribution {
    address public operator;

    struct DistributionRecord {
        uint256 distributionId;
        string projectId;
        uint256 totalAmount;        // Total revenue distributed (in cents / base units)
        uint256 timestamp;
        uint256 recipientCount;
    }

    struct ShareAllocation {
        address account;
        uint256 tokenAmount;        // Out of 100 total project tokens
        uint256 payoutAmount;       // Proportional payout
    }

    // Mapping from distributionId to DistributionRecord
    mapping(uint256 => DistributionRecord) public distributions;
    uint256 public nextDistributionId = 1;

    // Events emitted for Hedera Mirror Node indexing and on-chain verification
    event RevenueDistributed(
        uint256 indexed distributionId,
        string indexed projectId,
        uint256 totalAmount,
        uint256 recipientCount,
        uint256 timestamp
    );

    event RecipientPayout(
        uint256 indexed distributionId,
        address indexed recipient,
        uint256 tokenCount,
        uint256 payoutAmount
    );

    modifier onlyOperator() {
        require(msg.sender == operator, "Caller is not the authorized EnerX backend operator");
        _;
    }

    constructor() {
        operator = msg.sender;
    }

    /**
     * @notice Distribute revenue to token holders based on current token ownership.
     * @param projectId The unique project identifier.
     * @param recipients Array of recipient Hedera EVM addresses.
     * @param tokenAmounts Array of tokens held by each recipient (must sum to 100).
     * @param totalAmount Total revenue amount to distribute.
     */
    function recordDistribution(
        string calldata projectId,
        address[] calldata recipients,
        uint256[] calldata tokenAmounts,
        uint256 totalAmount
    ) external onlyOperator returns (uint256 distributionId) {
        require(recipients.length == tokenAmounts.length, "Mismatched recipients and token counts");
        require(recipients.length > 0, "At least one recipient required");
        require(totalAmount > 0, "Total amount must be greater than zero");

        uint256 totalTokens = 0;
        uint256 totalAllocated = 0;

        for (uint256 i = 0; i < recipients.length; i++) {
            totalTokens += tokenAmounts[i];
            totalAllocated += (totalAmount * tokenAmounts[i]) / 100;
        }

        require(totalTokens == 100, "Project tokens must sum exactly to 100 (100% ownership)");

        uint256 remainingUnits = totalAmount - totalAllocated;
        distributionId = nextDistributionId++;

        for (uint256 i = 0; i < recipients.length; i++) {
            uint256 payout = (totalAmount * tokenAmounts[i]) / 100;
            if (i < remainingUnits) {
                payout += 1;
            }
            emit RecipientPayout(distributionId, recipients[i], tokenAmounts[i], payout);
        }

        distributions[distributionId] = DistributionRecord({
            distributionId: distributionId,
            projectId: projectId,
            totalAmount: totalAmount,
            timestamp: block.timestamp,
            recipientCount: recipients.length
        });

        emit RevenueDistributed(
            distributionId,
            projectId,
            totalAmount,
            recipients.length,
            block.timestamp
        );

        return distributionId;
    }

    /**
     * @notice Fetch record of a past distribution.
     */
    function getDistribution(uint256 distributionId) external view returns (DistributionRecord memory) {
        require(distributions[distributionId].distributionId != 0, "Distribution not found");
        return distributions[distributionId];
    }
}
