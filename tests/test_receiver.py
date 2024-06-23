import ape
from ape import Contract
from utils.constants import MAX_BPS
import pytest


PRECISION = 10**18


def test_receiver(
    chain,
    receiver1,
    trade_factory,
    ylockers_ms,
    gov,
    dev,
    crvusd,
    crvusd_whale,
    crv,
    crv_whale,
    spell,
    spell_whale,
):
    # stock our fee distributor w/ good tokens
    crvusd.transfer(receiver1, 10_000 * PRECISION, sender=crvusd_whale)
    crv.transfer(receiver1, 10_000 * PRECISION, sender=crv_whale)
    spell.transfer(receiver1, 10_000 * PRECISION, sender=spell_whale)

    spell_starting = spell.balanceOf(receiver1)
    crv_starting = crv.balanceOf(receiver1)
    crvusd_starting = crvusd.balanceOf(receiver1)

    # check that an unapproved factory can't do anything
    assert receiver1.isTokenSpender(trade_factory) == False
    with ape.reverts("revert: Ownable: caller is not the owner"):
        receiver1.approveTokenSpender(trade_factory, sender=ylockers_ms)

    # approve trade factory as a spender
    receiver1.approveTokenSpender(trade_factory, sender=gov)
    assert receiver1.isTokenSpender(trade_factory) == True

    # still can't pull out tokens
    with ape.reverts():
        crv.transferFrom(
            receiver1, trade_factory, 10_000 * PRECISION, sender=trade_factory
        )
    with ape.reverts():
        crvusd.transferFrom(
            receiver1, trade_factory, 10_000 * PRECISION, sender=trade_factory
        )
    with ape.reverts("revert: ERC20: allowance too low"):
        spell.transferFrom(
            receiver1, trade_factory, 10_000 * PRECISION, sender=trade_factory
        )

    # trade factory can't give themselves new token approvals!
    with ape.reverts("revert: not approved"):
        receiver1.giveTokenAllowance(trade_factory, [crv, crvusd], sender=trade_factory)

    # accidentally pass in our own address, whoops
    with ape.reverts("revert: unapproved spender"):
        receiver1.giveTokenAllowance(ylockers_ms, [crv, crvusd], sender=ylockers_ms)

    # give approval for crv and crvUSD
    receiver1.giveTokenAllowance(trade_factory, [crv, crvusd], sender=ylockers_ms)
    print(
        "\nCRV Approval amount:",
        crv.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "crvUSD Approval amount:",
        crvusd.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "SPELL Approval amount:",
        spell.allowance(receiver1, trade_factory) / PRECISION,
        "\n",
    )

    # should be able to pull out crv and crvUSD, not spell
    to_pull = 1_000 * PRECISION
    crv.transferFrom(receiver1, trade_factory, to_pull, sender=trade_factory)
    assert crv.balanceOf(receiver1) == crv_starting - to_pull
    crv_current = crv.balanceOf(receiver1)
    crvusd.transferFrom(receiver1, trade_factory, to_pull, sender=trade_factory)
    assert crvusd.balanceOf(receiver1) == crvusd_starting - to_pull
    crvusd_current = crvusd.balanceOf(receiver1)
    with ape.reverts("revert: ERC20: allowance too low"):
        spell.transferFrom(
            receiver1, trade_factory, 10_000 * PRECISION, sender=trade_factory
        )

    # check the approvals we currently have
    approvals = receiver1.getApprovals(trade_factory)
    print("Trade Factory approvals:", approvals)
    assert len(approvals) == 2
    approvals = receiver1.getApprovals(ylockers_ms)
    print("yLockers approvals:", approvals)
    assert len(approvals) == 0

    # make sure nothing happens if we accidentally re-approve
    receiver1.giveTokenAllowance(trade_factory, [crv, crvusd], sender=ylockers_ms)
    print("\nRe-give the same token allowances")
    print(
        "CRV Approval amount:",
        crv.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "crvUSD Approval amount:",
        crvusd.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "SPELL Approval amount:",
        spell.allowance(receiver1, trade_factory) / PRECISION,
        "\n",
    )

    # revoke a token allowance. doesn't necessarily have to be for a spender.
    receiver1.revokeTokenAllowance(trade_factory, [crv], sender=ylockers_ms)
    print("\nRevoke allowance for only CRV")
    print(
        "CRV Approval amount:",
        crv.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "crvUSD Approval amount:",
        crvusd.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "SPELL Approval amount:",
        spell.allowance(receiver1, trade_factory) / PRECISION,
        "\n",
    )

    # we should be able to revoke for an address with no approvals too, and also for tokens with no approval
    receiver1.revokeTokenAllowance(trade_factory, [spell, crv], sender=ylockers_ms)
    receiver1.revokeTokenAllowance(ylockers_ms, [spell, crv], sender=gov)
    print("\nCheck after revoking already revoked tokens")
    print(
        "CRV Approval amount:",
        crv.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "crvUSD Approval amount:",
        crvusd.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "SPELL Approval amount:",
        spell.allowance(receiver1, trade_factory) / PRECISION,
        "\n",
    )

    print("\nCheck yLockers MS (non-spender) approvals after revoking them")
    print(
        "CRV Approval amount:",
        crv.allowance(receiver1, ylockers_ms) / PRECISION,
    )
    print(
        "crvUSD Approval amount:",
        crvusd.allowance(receiver1, ylockers_ms) / PRECISION,
    )
    print(
        "SPELL Approval amount:",
        spell.allowance(receiver1, ylockers_ms) / PRECISION,
        "\n",
    )

    # make sure we can re-grant approvals to spender
    receiver1.giveTokenAllowance(trade_factory, [spell, crv, crvusd], sender=gov)
    print("\nCheck after re-giving and adding approvals for trade factory")
    print(
        "CRV Approval amount:",
        crv.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "crvUSD Approval amount:",
        crvusd.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "SPELL Approval amount:",
        spell.allowance(receiver1, trade_factory) / PRECISION,
        "\n",
    )

    # check then revoke trade factory's spender status and approvals, bad trade factory!
    approvals = receiver1.getApprovals(trade_factory)
    print("Trade Factory approvals:", approvals)
    assert len(approvals) == 3

    # not just anyone can revert their approval
    with ape.reverts("revert: not approved"):
        receiver1.revokeTokenSpender(trade_factory, sender=dev)

    # can't revoke an address that isn't a spender
    with ape.reverts("revert: not a spender"):
        receiver1.revokeTokenSpender(ylockers_ms, sender=gov)

    receiver1.revokeTokenSpender(trade_factory, sender=ylockers_ms)
    assert receiver1.isTokenSpender(trade_factory) == False
    approvals = receiver1.getApprovals(trade_factory)
    print("Trade Factory approvals:", approvals)
    assert len(approvals) == 0

    print("\nCheck after removing trade factory as a spender")
    print(
        "CRV Approval amount:",
        crv.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "crvUSD Approval amount:",
        crvusd.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "SPELL Approval amount:",
        spell.allowance(receiver1, trade_factory) / PRECISION,
        "\n",
    )

    # update guardian role, make sure only owner can
    with ape.reverts("revert: Ownable: caller is not the owner"):
        receiver1.setGuardian(dev, sender=dev)
    receiver1.setGuardian(dev, sender=gov)

    # ylockers ms should be locked out now
    with ape.reverts("revert: not approved"):
        receiver1.giveTokenAllowance(trade_factory, [crv, crvusd], sender=ylockers_ms)

    # now some random dev has the power
    with ape.reverts("revert: unapproved spender"):
        receiver1.giveTokenAllowance(trade_factory, [crv, crvusd], sender=dev)

    # gov still has the approve new spenders
    with ape.reverts("revert: Ownable: caller is not the owner"):
        receiver1.approveTokenSpender(trade_factory, sender=dev)
    receiver1.approveTokenSpender(trade_factory, sender=gov)

    receiver1.giveTokenAllowance(trade_factory, [crv, crvusd], sender=dev)
    print("\nReenable trade factory again after removing them as a spender")
    print(
        "CRV Approval amount:",
        crv.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "crvUSD Approval amount:",
        crvusd.allowance(receiver1, trade_factory) / PRECISION,
    )
    print(
        "SPELL Approval amount:",
        spell.allowance(receiver1, trade_factory) / PRECISION,
        "\n",
    )
