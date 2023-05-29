from utils import harvest_strategy
import ape
from ape import Contract, project, config, chain, accounts
from ape.utils.misc import ZERO_ADDRESS


# test our permissionless swaps and our trade handler functions as intended
def test_keepers_and_trade_handler(
    gov,
    token,
    vault,
    whale,
    strategy,
    amount,
    sleep_time,
    profit_whale,
    profit_amount,
    target,
    use_yswaps,
    keeper_wrapper,
    trade_factory,
    lusd_whale,
):
    # no testing needed if we're not using yswaps
    if not use_yswaps:
        return

    ## deposit to the vault after approving
    starting_whale = token.balanceOf(whale)
    token.approve(vault, 2**256 - 1, sender=whale)
    vault.deposit(amount, sender=whale)
    newWhale = token.balanceOf(whale)

    # harvest, store asset amount
    (profit, loss) = harvest_strategy(
        use_yswaps,
        strategy,
        token,
        gov,
        profit_whale,
        profit_amount,
        target,
    )

    # simulate profits
    chain.mine(sleep_time)
    chain.mine(1)

    # harvest, store new asset amount
    (profit, loss) = harvest_strategy(
        use_yswaps,
        strategy,
        token,
        gov,
        profit_whale,
        profit_amount,
        target,
    )

    # set our keeper up
    strategy.setKeeper(keeper_wrapper, sender=gov)

    # here we make sure we can harvest through our keeper wrapper
    keeper_wrapper.harvest(strategy, sender=profit_whale)

    ####### ADD LOGIC AS NEEDED FOR SENDING REWARDS TO STRATEGY #######
    # send our strategy some LUSD. normally it would be sitting waiting for trade handler but we automatically process it
    lusd = project.IERC20.at(strategy.lusd())
    lusd.transfer(strategy, 100 * 10**18, sender=lusd_whale)

    # whale can't sweep, but trade handler can
    with ape.reverts():
        lusd.transferFrom(
            strategy, whale, int(lusd.balanceOf(strategy) / 2), sender=whale
        )

    lusd.transferFrom(
        strategy, whale, int(lusd.balanceOf(strategy) / 2), sender=trade_factory
    )

    # remove our trade handler
    strategy.removeTradeFactoryPermissions(True, sender=gov)
    assert strategy.tradeFactory() == ZERO_ADDRESS
    assert lusd.balanceOf(strategy) > 0

    # trade factory now cant sweep
    with ape.reverts():
        lusd.transferFrom(
            strategy, whale, int(lusd.balanceOf(strategy) / 2), sender=trade_factory
        )

    # give back those permissions, now trade factory can sweep
    strategy.updateTradeFactory(trade_factory, sender=gov)
    lusd.transferFrom(
        strategy, whale, int(lusd.balanceOf(strategy) / 2), sender=trade_factory
    )

    # remove again!
    strategy.removeTradeFactoryPermissions(False, sender=gov)

    # update again
    strategy.updateTradeFactory(trade_factory, sender=gov)

    # simulate profits
    chain.mine(sleep_time)
    chain.mine(1)

    # can't set trade factory to zero
    with ape.reverts():
        strategy.updateTradeFactory(ZERO_ADDRESS, sender=gov)

    # update our rewards to just LUSD
    strategy.updateRewards([strategy.lusd()], sender=gov)
    assert strategy.rewardsTokens(0) == strategy.lusd()

    # don't have another token here anymore
    with ape.reverts():
        assert strategy.rewardsTokens(1) == ZERO_ADDRESS

    # only gov can update rewards
    with ape.reverts():
        strategy.updateRewards([strategy.lusd()], sender=whale)
