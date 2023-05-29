import pytest
from ape import Contract, project, config, chain, accounts
import requests
from ape.utils.misc import ZERO_ADDRESS


# set this for if we want to use tenderly or not; mostly helpful because with brownie.reverts fails in tenderly forks.
use_tenderly = False

# use this to set what chain we use. 1 for ETH, 250 for fantom, 10 optimism, 42161 arbitrum
chain_used = 1


################################################## TENDERLY DEBUGGING ##################################################


# change autouse to True if we want to use this fork to help debug tests
@pytest.fixture(scope="session", autouse=use_tenderly)
def tenderly_fork(web3, chain):
    fork_base_url = "https://simulate.yearn.network/fork"
    payload = {"network_id": str(chain.id)}
    resp = requests.post(fork_base_url, headers={}, json=payload)
    fork_id = resp.json()["simulation_fork"]["id"]
    fork_rpc_url = f"https://rpc.tenderly.co/fork/{fork_id}"
    print(fork_rpc_url)
    tenderly_provider = web3.HTTPProvider(fork_rpc_url, {"timeout": 600})
    web3.provider = tenderly_provider
    print(f"https://dashboard.tenderly.co/yearn/yearn-web/fork/{fork_id}")


################################################ UPDATE THINGS BELOW HERE ################################################

#################### FIXTURES BELOW NEED TO BE ADJUSTED FOR THIS REPO ####################


@pytest.fixture(scope="session")
def token():
    token_address = "0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D"  # this should be the address of the ERC-20 used by the strategy/vault (LQTY)
    yield Contract(token_address)


@pytest.fixture(scope="session")
def whale(amount, token):
    # Totally in it for the tech
    # Update this with a large holder of your want token (the largest EOA holder of LP)
    whale = accounts[
        "0x83b1eC6cc7D44bb9BA1A48c53AB0337cAE5A0DBe"
    ]  # 0x83b1eC6cc7D44bb9BA1A48c53AB0337cAE5A0DBe, LQTY, 9.8m tokens
    if token.balanceOf(whale) < 2 * amount:
        raise ValueError(
            "Our whale needs more funds. Find another whale or reduce your amount variable."
        )
    yield whale


@pytest.fixture(scope="session")
def amount(token):
    amount = 50_000 * 10 ** token.decimals()
    yield amount


@pytest.fixture(scope="session")
def profit_whale(profit_amount, token):
    # ideally not the same whale as the main whale, or else they will lose money
    profit_whale = accounts[
        "0xD8c9D9071123a059C6E0A945cF0e0c82b508d816"
    ]  # 0xD8c9D9071123a059C6E0A945cF0e0c82b508d816, LQTY, 8.7m tokens
    if token.balanceOf(profit_whale) < 5 * profit_amount:
        raise ValueError(
            "Our profit whale needs more funds. Find another whale or reduce your profit_amount variable."
        )
    yield profit_whale


@pytest.fixture(scope="session")
def profit_amount(token):
    profit_amount = 50 * 10 ** token.decimals()
    yield profit_amount


# set address if already deployed, use ZERO_ADDRESS if not
@pytest.fixture(scope="session")
def vault_address():
    vault_address = ZERO_ADDRESS
    yield vault_address


# if our vault is pre-0.4.3, this will affect a few things
@pytest.fixture(scope="session")
def old_vault():
    old_vault = False
    yield old_vault


# this is the name we want to give our strategy
@pytest.fixture(scope="session")
def strategy_name():
    strategy_name = "StrategyLQTYStaker"
    yield strategy_name


# this is the name of our strategy in the .sol file
@pytest.fixture(scope="session")
def contract_name():
    contract_name = project.StrategyLQTYStaker
    yield contract_name


# if our strategy is using ySwaps, then we need to donate profit to it from our profit whale
@pytest.fixture(scope="session")
def use_yswaps():
    use_yswaps = True
    yield use_yswaps


# whether or not a strategy is clonable. if true, don't forget to update what our cloning function is called in test_cloning.py
@pytest.fixture(scope="session")
def is_clonable():
    is_clonable = False
    yield is_clonable


# use this to test our strategy in case there are no profits
@pytest.fixture(scope="session")
def no_profit():
    no_profit = False
    yield no_profit


# use this when we might lose a few wei on conversions between want and another deposit token (like router strategies)
# generally this will always be true if no_profit is true, even for curve/convex since we can lose a wei converting
@pytest.fixture(scope="session")
def is_slippery(no_profit):
    is_slippery = False  # set this to true or false as needed
    if no_profit:
        is_slippery = True
    yield is_slippery


# use this to set the standard amount of time we sleep between harvests.
# generally 1 day, but can be less if dealing with smaller windows (oracles) or longer if we need to trigger weekly earnings.
@pytest.fixture(scope="session")
def sleep_time():
    hour = 3600

    # change this one right here
    hours_to_sleep = 24

    sleep_time = hour * hours_to_sleep
    yield sleep_time


#################### FIXTURES ABOVE NEED TO BE ADJUSTED FOR THIS REPO ####################

#################### FIXTURES BELOW SHOULDN'T NEED TO BE ADJUSTED FOR THIS REPO ####################


@pytest.fixture(scope="session")
def tests_using_tenderly():
    yes_or_no = use_tenderly
    yield yes_or_no


# by default, pytest uses decimals, but in solidity we use uints, so 10 actually equals 10 wei (1e-17 for most assets, or 1e-6 for USDC/USDT)
@pytest.fixture
def RELATIVE_APPROX(token):
    approx = 10
    print("\nApprox:", approx, "wei")
    yield approx


# use this to set various fixtures that differ by chain
if chain_used == 1:  # mainnet

    @pytest.fixture
    def gov(accounts, ether_whale):
        gov = accounts["0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52"]
        ether_whale.transfer(gov, 100 * 10**18)
        yield gov

    @pytest.fixture(scope="session")
    def health_check():
        yield Contract("0xddcea799ff1699e98edf118e0629a974df7df012")

    @pytest.fixture(scope="session")
    def base_fee_oracle():
        yield Contract("0xfeCA6895DcF50d6350ad0b5A8232CF657C316dA7")

    @pytest.fixture
    def ether_whale(accounts):
        yield accounts["0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8"]

    # set all of the following to a fresh account, so we don't have to worry about it being funded
    @pytest.fixture
    def management(accounts, ether_whale):
        management = accounts["0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7"]
        ether_whale.transfer(management, 100 * 10**18)
        yield management

    @pytest.fixture
    def rewards(management):
        yield management

    @pytest.fixture
    def guardian(management):
        yield management

    @pytest.fixture
    def strategist(management):
        yield management

    @pytest.fixture
    def keeper(management):
        yield management

    @pytest.fixture(scope="session")
    def to_sweep():
        # token we can sweep out of strategy (use CRV)
        yield Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")

    @pytest.fixture(scope="session")
    def trade_factory():
        yield Contract("0xcADBA199F3AC26F67f660C89d43eB1820b7f7a3b")

    @pytest.fixture(scope="session")
    def keeper_wrapper():
        yield Contract("0x0D26E894C2371AB6D20d99A65E991775e3b5CAd7")


@pytest.fixture
def vault(gov, rewards, guardian, management, token, vault_address):
    print(" ")  # do this so the first deployment is on a new line
    if vault_address == ZERO_ADDRESS:
        vault = guardian.deploy(project.dependencies["yearnvaults"]["master"].Vault)
        vault.initialize(token, gov, rewards, "", "", sender=gov)
        vault.setDepositLimit(2**256 - 1, sender=gov)
        vault.setManagement(management, sender=gov)
    else:
        vault = Contract(vault_address)
    yield vault


#################### FIXTURES ABOVE SHOULDN'T NEED TO BE ADJUSTED FOR THIS REPO ####################

#################### FIXTURES BELOW LIKELY NEED TO BE ADJUSTED FOR THIS REPO ####################


@pytest.fixture(scope="session")
def target():
    # whatever we want it to be—this is passed into our harvest function as a target
    yield 9


# this should be a strategy from a different vault to check during migration
@pytest.fixture(scope="session")
def other_strategy():
    yield Contract("0x3bCa26c3D49Af712ac74Af82De27665A610999E2")


@pytest.fixture
def strategy(
    strategist,
    keeper,
    vault,
    gov,
    management,
    health_check,
    contract_name,
    strategy_name,
    base_fee_oracle,
    vault_address,
    trade_factory,
    ether_whale,
):
    # will need to update this based on the strategy's constructor ******
    strategy = gov.deploy(
        project.StrategyLQTYStaker,
        vault,
        trade_factory,
        10_000 * 10**6,
        50_000 * 10**6,
    )

    strategy.setKeeper(keeper, sender=gov)
    strategy.setHealthCheck(health_check, sender=gov)
    strategy.setDoHealthCheck(True, sender=gov)
    vault.setPerformanceFee(0, sender=gov)
    vault.setManagementFee(0, sender=gov)

    # if we have other strategies, set them to zero DR and remove them from the queue
    if vault_address != ZERO_ADDRESS:
        for i in range(0, 20):
            strat_address = vault.withdrawalQueue(i)
            if ZERO_ADDRESS == strat_address:
                break

            if vault.strategies(strat_address)["debtRatio"] > 0:
                vault.updateStrategyDebtRatio(strat_address, 0, sender=gov)
                Contract(strat_address).harvest(sender=gov)
                vault.removeStrategyFromQueue(strat_address, sender=gov)

    vault.addStrategy(strategy, 10_000, 0, 2**256 - 1, 0, sender=gov)

    # turn our oracle into testing mode by setting the provider to 0x00, then forcing true
    strategy.setBaseFeeOracle(base_fee_oracle, sender=management)
    base_fee_oracle.setBaseFeeProvider(
        ZERO_ADDRESS, sender=base_fee_oracle.governance()
    )
    base_fee_oracle.setManualBaseFeeBool(True, sender=base_fee_oracle.governance())
    assert strategy.isBaseFeeAcceptable() == True

    yield strategy


#################### FIXTURES ABOVE LIKELY NEED TO BE ADJUSTED FOR THIS REPO ####################

####################         PUT UNIQUE FIXTURES FOR THIS REPO BELOW         ####################


@pytest.fixture
def booster(
    strategy,
    gov,
    rewards,
    guardian,
    management,
    token,
    vault_address,
):
    booster = gov.deploy(project.yLQTYBooster, strategy)
    yield booster


@pytest.fixture(scope="session")
def lusd_whale():
    return accounts["0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1"]
