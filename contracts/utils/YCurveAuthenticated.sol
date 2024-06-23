// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "../interfaces/ILocker.sol";

/**
    @title YLockers Authentication
    @author Yearn Finance
    @notice Contracts inheriting permit only a trusted set of callers.
 */
contract YCurveAuthenticated {
    ILocker public immutable LOCKER;

    constructor(address _locker) {
        LOCKER = ILocker(_locker);
    }

    modifier enforceAuth() {
        require(isAuthenticated(msg.sender), "!authorized");
        _;
    }

    function isAuthenticated(address _caller) public view returns (bool) {
        return (_caller == LOCKER.governance() || _caller == address(LOCKER));
    }
}
