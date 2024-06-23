// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {IERC20, SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {EnumerableSet} from "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";
import {YCurveAuthenticated} from "utils/YCurveAuthenticated.sol";

/**
    @title Yearn Curve Fee Receiver
    @author Yearn Finance
    @notice Recipient contract for tokens earned by Yearn's veCRV position.
 */
contract YCurveFeeReceiver is YCurveAuthenticated {
    using SafeERC20 for IERC20;
    using EnumerableSet for EnumerableSet.AddressSet;

    ///@notice Check if an address is an approved guardian of this contract
    mapping(address => bool) public isGuardian;

    ///@notice Check if an address is approved to spend tokens from this contract
    mapping(address => bool) public isTokenSpender;

    // spender => tokens they have been approved to spend
    mapping(address => EnumerableSet.AddressSet) internal spenderApprovals;

    constructor(address _locker) YCurveAuthenticated(_locker) {}

    /**
     * @notice Transfer out any token as needed
     * @dev Should only be used as an emergency function
     * @param _token Token to transfer out
     * @param _receiver Address to send the token to
     * @param _amount Amount of token to transfer
     */
    function transferToken(
        address _token,
        address _receiver,
        uint256 _amount
    ) external enforceAuth {
        IERC20(_token).safeTransfer(_receiver, _amount);
    }

    /**
     * @notice Approve (allowlist) an address to spend any token held by this contract.
     * @dev Use with great caution! Note that individual tokens must still be added.
     * @param _spender Address to allow to spend tokens
     */
    function approveTokenSpender(address _spender) external enforceAuth {
        isTokenSpender[_spender] = true;
    }

    /**
     * @notice Revoke future approval for an address to spend any token held by this contract.
     * @dev Note that this clears all of their existing approvals as well
     * @param _spender Address to revoke from spending tokens
     */
    function revokeTokenSpender(address _spender) external {
        require(
            isGuardian[msg.sender] || isAuthenticated(msg.sender),
            "not approved"
        );
        require(isTokenSpender[_spender], "already revoked");
        isTokenSpender[_spender] = false;

        // revoke all of their approvals as well
        address[] memory tokens = spenderApprovals[_spender].values();
        for (uint256 i; i < tokens.length; ++i) {
            IERC20(tokens[i]).forceApprove(_spender, 0);
            spenderApprovals[_spender].remove(tokens[i]);
        }
    }

    /**
     * @notice Grant guardian role to an address
     * @dev Guardian can add tokens for approved spenders, revoke spenders, and revoke tokens
     * @param _guardian Address to grant guardian role
     */
    function approveGuardian(address _guardian) external enforceAuth {
        isGuardian[_guardian] = true;
    }

    /**
     * @notice Revoke guardian role from an address
     * @param _guardian Address to revoke from guardian role
     */
    function revokeGuardian(address _guardian) external enforceAuth {
        isGuardian[_guardian] = false;
    }

    /**
     * @notice Approve a previously approved spender to spend a list of tokens
     * @param _spender Address to allow to spend tokens
     * @param _tokens Addresses of tokens to allow
     */
    function giveTokenAllowance(
        address _spender,
        address[] memory _tokens
    ) external {
        require(
            isGuardian[msg.sender] || isAuthenticated(msg.sender),
            "not approved"
        );
        require(isTokenSpender[_spender], "unapproved spender");
        for (uint256 i; i < _tokens.length; ++i) {
            IERC20(_tokens[i]).forceApprove(_spender, type(uint256).max);
            spenderApprovals[_spender].add(_tokens[i]);
        }
    }

    /**
     * @notice Revoke a previously approved spender from spending a list of tokens
     * @param _spender Address to revoke spending tokens
     * @param _tokens Addresses of tokens to revoke
     */
    function revokeTokenAllowance(
        address _spender,
        address[] memory _tokens
    ) external {
        require(
            isGuardian[msg.sender] || isAuthenticated(msg.sender),
            "not approved"
        );
        for (uint256 i; i < _tokens.length; ++i) {
            IERC20(_tokens[i]).forceApprove(_spender, 0);
            spenderApprovals[_spender].remove(_tokens[i]);
        }
    }

    /**
     * @notice Check if a spender has the ability to spend any tokens from this contract.
     * @param _spender Address to check for tokens approvals
     * @return tokens Addresses of tokens this spender can pull
     */
    function getApprovals(
        address _spender
    ) public returns (address[] memory tokens) {
        return spenderApprovals[_spender].values();
    }
}
