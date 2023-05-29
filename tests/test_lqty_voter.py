import pytest
import ape
from ape import Contract, project, config, chain, accounts
from utils import harvest_strategy


# this test module is specific to this strategy; other protocols may require similar extra contracts and/or testing
# test the our strategy's ability to deposit, harvest, and withdraw, with different optimal deposit tokens if we have them
# turn on keepLQTY for this version
def test_simple_harvest_keep(
    gov,
    token,
    vault,
    whale,
    strategy,
    amount,
    sleep_time,
    is_slippery,
    no_profit,
    profit_whale,
    profit_amount,
    target,
    use_yswaps,
    booster,
):
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
    old_assets = vault.totalAssets()
    assert old_assets > 0
    assert token.balanceOf(strategy) == 0
    assert strategy.estimatedTotalAssets() > 0

    # turn on keeping some LQTY for our booster
    strategy.setBooster(booster, sender=gov)

    # simulate profits
    chain.mine(sleep_time)

    # check our name for fun (jk, for coverage)
    name = booster.name()
    print("Name:", name)

    # re-set strategy
    booster.setStrategy(strategy, sender=gov)

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

    # need second harvest to get some profits sent to booster (ySwaps)
    (profit, loss) = harvest_strategy(
        use_yswaps,
        strategy,
        token,
        gov,
        profit_whale,
        profit_amount,
        target,
    )

    # check that our booster got its lqty
    assert booster.stakedBalance() > 0

    ################# GENERATE CLAIMABLE PROFIT HERE AS NEEDED #################
    # we simulate minting LUSD fees from liquity's borrower operations to the staking contract
    lusd_borrower = accounts["0xaC5406AEBe35A27691D62bFb80eeFcD7c0093164"]
    borrower_operations = accounts["0x24179CD81c9e782A4096035f7eC97fB8B783e007"]
    staking = Contract("0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d")
    before = staking.getPendingLUSDGain(lusd_borrower)
    staking.increaseF_LUSD(100_000 * 10**18, sender=borrower_operations)
    after = staking.getPendingLUSDGain(lusd_borrower)
    assert after > before

    # check that we have claimable profit on our booster
    claimable_lusd = staking.getPendingLUSDGain(booster)
    print("Claimable LUSD:", claimable_lusd / 10**18)

    # simulate profits
    chain.mine(sleep_time)

    # need second harvest to get some profits sent to booster (ySwaps)
    (profit, loss) = harvest_strategy(
        use_yswaps,
        strategy,
        token,
        gov,
        profit_whale,
        profit_amount,
        target,
    )

    # set our keep to zero
    strategy.setKeepLqty(0, sender=gov)

    # simulate profits
    chain.mine(sleep_time)

    # harvest so we get one with no keep
    (profit, loss) = harvest_strategy(
        use_yswaps,
        strategy,
        token,
        gov,
        profit_whale,
        profit_amount,
        target,
    )

    # record this here so it isn't affected if we donate via ySwaps
    strategy_assets = strategy.estimatedTotalAssets()

    # harvest again so the strategy reports the final bit of profit for yswaps
    if use_yswaps:
        print("Using ySwaps for harvests")
        (profit, loss) = harvest_strategy(
            use_yswaps,
            strategy,
            token,
            gov,
            profit_whale,
            profit_amount,
            target,
        )

    # evaluate our current total assets
    new_assets = vault.totalAssets()

    # confirm we made money, or at least that we have about the same
    if is_slippery and no_profit:
        assert pytest.approx(new_assets, rel=RELATIVE_APPROX) == old_assets
    else:
        new_assets >= old_assets

    # simulate five days of waiting for share price to bump back up
    chain.mine(86400 * 5)
    chain.mine(1)

    # Display estimated APR
    print(
        "\nEstimated APR: ",
        "{:.2%}".format(
            ((new_assets - old_assets) * (365 * 86400 / sleep_time)) / (strategy_assets)
        ),
    )

    # withdraw and confirm we made money, or at least that we have about the same
    vault.withdraw(sender=whale)
    if is_slippery and no_profit:
        assert (
            pytest.approx(token.balanceOf(whale), rel=RELATIVE_APPROX) == starting_whale
        )
    else:
        assert token.balanceOf(whale) >= starting_whale


# test sweeping out tokens
def test_sweeps_and_harvest(
    gov,
    token,
    vault,
    whale,
    strategy,
    to_sweep,
    amount,
    profit_whale,
    profit_amount,
    target,
    use_yswaps,
    lusd_whale,
    booster,
):
    # collect our tokens
    lqty = project.IERC20.at(strategy.lqty())
    lusd = project.IERC20.at(strategy.lusd())

    # lusd whale sends lusd to our booster
    lusd.transfer(booster, 2000 * 10**18, sender=lusd_whale)

    # we can sweep out any non-want
    booster.sweep(strategy.lusd(), sender=gov)

    # lusd whale sends ether and lusd to our booster, profit whale sends in lqty
    lusd.transfer(booster, 2000 * 10**18, sender=lusd_whale)
    lusd_whale.transfer(booster, 10**18)
    lqty.transfer(booster, 100 * 10**18, sender=profit_whale)

    # we can sweep out any non-want, do twice for zero sweep
    booster.sweep(strategy.lusd(), sender=gov)
    booster.sweep(strategy.lusd(), sender=gov)

    # only gov can sweep
    with ape.reverts():
        booster.sweep(strategy.lusd(), sender=whale)

    # not even gov can sweep lqty
    with ape.reverts():
        booster.sweep(strategy.lqty(), sender=gov)

    # lusd whale sends more lusd to our booster
    lusd.transfer(booster, 2000 * 10**18, sender=lusd_whale)

    # can't do it before we sleep, for some reason coverage doesn't pick up on this 🤔
    assert chain.pending_timestamp < booster.unstakeQueued() + (14 * 86400)

    # this is currently commented out, ape treats this as an exception due to overflow, not a revert, need to find a way to account for that
    #     with ape.reverts():
    #         booster.unstakeAndSweep(2**256 - 1, sender=gov)

    # queue our sweep, gotta wait two weeks before we can sweep tho
    booster.queueSweep(sender=gov)
    chain.mine(86400 * 15)
    chain.mine(1)

    # lock some lqty, but only strategy can
    with ape.reverts():
        booster.strategyHarvest(sender=gov)
    booster.strategyHarvest(sender=strategy)

    # sweep!
    booster.unstakeAndSweep(booster.stakedBalance(), sender=gov)

    # only gov can sweep
    with ape.reverts():
        booster.unstakeAndSweep(booster.stakedBalance(), sender=whale)

    chain.mine(1)
    chain.mine(1)

    # harvest with no stake and no lqty
    booster.strategyHarvest(sender=strategy)

    # check
    assert booster.stakedBalance() == 0

    # harvest with no stake and some lqty
    lqty.transfer(booster, 100 * 10**18, sender=profit_whale)
    booster.strategyHarvest(sender=strategy)

    # check
    assert booster.stakedBalance() > 0
    booster.strategyHarvest(sender=strategy)

    # sweep again!
    booster.unstakeAndSweep(2**256 - 1, sender=gov)

    # sweep again!
    booster.unstakeAndSweep(2**256 - 1, sender=gov)

    # check
    assert booster.stakedBalance() == 0

    # one last harvest
    booster.strategyHarvest(sender=strategy)

    # lusd whale sends ether and lusd to our booster
    lusd.transfer(booster, 2000 * 10**18, sender=lusd_whale)
    lusd_whale.transfer(booster, 10**18)

    # send it back out
    booster.unstakeAndSweep(2**256 - 1, sender=gov)

    # send in more
    lusd.transfer(booster, 2000 * 10**18, sender=lusd_whale)
    lusd_whale.transfer(booster, 10**18)

    # booster should have balance, then we harvest to make it go away (to strategy)
    assert booster.balance > 0
    booster.strategyHarvest(sender=strategy)
    assert booster.balance == 0

    # can't sweep if we wait too long, oops
    chain.mine(14 * 86400)
    with ape.reverts():
        booster.unstakeAndSweep(2**256 - 1, sender=gov)
