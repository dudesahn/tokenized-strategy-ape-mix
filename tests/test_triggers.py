import pytest
from utils import harvest_strategy
import ape
from ape import Contract, project, config, chain, accounts


# test our harvest triggers
def test_triggers(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    amount,
    sleep_time,
    is_slippery,
    no_profit,
    profit_whale,
    profit_amount,
    target,
    base_fee_oracle,
    use_yswaps,
):
    # inactive strategy (0 DR and 0 assets) shouldn't be touched by keepers
    currentDebtRatio = vault.strategies(strategy)["debtRatio"]
    vault.updateStrategyDebtRatio(strategy, 0, sender=gov)
    (profit, loss) = harvest_strategy(
        use_yswaps,
        strategy,
        token,
        gov,
        profit_whale,
        profit_amount,
        target,
    )
    tx = strategy.harvestTrigger(0, sender=gov)
    print("\nShould we harvest? Should be false.", tx)
    assert tx == False
    vault.updateStrategyDebtRatio(strategy, currentDebtRatio, sender=gov)

    ## deposit to the vault after approving, no harvest yet
    starting_whale = token.balanceOf(whale)
    token.approve(vault, 2**256 - 1, sender=whale)
    vault.deposit(amount, sender=whale)
    newWhale = token.balanceOf(whale)
    starting_assets = vault.totalAssets()

    # update our min credit so harvest triggers true
    strategy.setCreditThreshold(1, sender=gov)
    tx = strategy.harvestTrigger(0, sender=gov)
    print("\nShould we harvest? Should be true.", tx)
    assert tx == True
    strategy.setCreditThreshold(int(1e24), sender=gov)

    # test our manual harvest trigger
    strategy.setForceHarvestTriggerOnce(True, sender=gov)
    tx = strategy.harvestTrigger(0, sender=gov)
    print("\nShould we harvest? Should be true.", tx)
    assert tx == True

    # harvest the credit
    (profit, loss) = harvest_strategy(
        use_yswaps,
        strategy,
        token,
        gov,
        profit_whale,
        profit_amount,
        target,
    )

    # should trigger false, nothing is ready yet, just harvested
    tx = strategy.harvestTrigger(0, sender=gov)
    print("\nShould we harvest? Should be false.", tx)
    assert tx == False

    # simulate earnings
    chain.mine(sleep_time)

    ################# GENERATE CLAIMABLE PROFIT HERE AS NEEDED #################
    # we simulate minting LUSD fees from liquity's borrower operations to the staking contract so we have claimable yield
    lusd_borrower = accounts["0xaC5406AEBe35A27691D62bFb80eeFcD7c0093164"]
    borrower_operations = accounts["0x24179CD81c9e782A4096035f7eC97fB8B783e007"]
    staking = Contract("0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d")
    before = staking.getPendingLUSDGain(lusd_borrower)
    staking.increaseF_LUSD(100_000 * 10**18, sender=borrower_operations)
    after = staking.getPendingLUSDGain(lusd_borrower)
    assert after > before

    # check that we have claimable profit, need this for min and max profit checks below
    claimable_profit = strategy.claimableProfitInUsdc()
    assert claimable_profit > 0
    claimable_lusd = staking.getPendingLUSDGain(strategy)
    assert claimable_lusd > 0

    if not (is_slippery and no_profit):
        # update our minProfit so our harvest triggers true
        strategy.setHarvestTriggerParams(1, 100_000 * 10**6, sender=gov)
        tx = strategy.harvestTrigger(0, sender=gov)
        print("\nShould we harvest? Should be true.", tx)
        assert tx == True

        # update our maxProfit so harvest triggers true
        strategy.setHarvestTriggerParams(100_000 * 10**6, 1, sender=gov)
        tx = strategy.harvestTrigger(0, sender=gov)
        print("\nShould we harvest? Should be true.", tx)
        assert tx == True
        strategy.setHarvestTriggerParams(
            90_000 * 10**6, 150_000 * 10**6, sender=gov
        )

    # set our max delay to 1 day so we trigger true, then set it back to 21 days
    strategy.setMaxReportDelay(sleep_time - 1, sender=gov)
    tx = strategy.harvestTrigger(0, sender=gov)
    print("\nShould we harvest? Should be True.", tx)
    assert tx == True
    strategy.setMaxReportDelay(86400 * 21, sender=gov)

    # harvest, wait
    (profit, loss) = harvest_strategy(
        use_yswaps,
        strategy,
        token,
        gov,
        profit_whale,
        profit_amount,
        target,
    )
    print("Profit:", profit, "Loss:", loss)
    chain.mine(sleep_time)

    # harvest should trigger false because of oracle
    base_fee_oracle.setManualBaseFeeBool(False, sender=gov)
    tx = strategy.harvestTrigger(0, sender=gov)
    print("\nShould we harvest? Should be false.", tx)
    assert tx == False
    base_fee_oracle.setManualBaseFeeBool(True, sender=gov)

    # simulate five days of waiting for share price to bump back up
    chain.mine(86400 * 5)
    chain.mine(1)

    # withdraw and confirm we made money, or at least that we have about the same
    vault.withdraw(sender=whale)
    if is_slippery and no_profit:
        assert (
            pytest.approx(token.balanceOf(whale), rel=RELATIVE_APPROX) == starting_whale
        )
    else:
        assert token.balanceOf(whale) >= starting_whale
