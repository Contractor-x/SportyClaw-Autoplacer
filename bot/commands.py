from datetime import datetime

from bankroll import get_state


def format_health_text(stats: dict) -> str:
    state = get_state()
    return (
        "Bot status: OK\n"
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Bets today: placed={stats['placed']} won={stats['won']} lost={stats['lost']} ongoing={stats['ongoing']}\n"
        f"Profit: N{stats['profit']:,.2f} / Loss: N{stats['loss']:,.2f}\n"
        f"Account balance: N{state['current_balance']:,.2f}\n"
        f"Starting balance: N{state['starting_balance']:,.2f}\n"
        f"Daily allocation: N{state['allocation_remaining']:,.2f} remaining / N{state['allocation_total']:,.2f} total\n"
        f"Bets left today: {state['bets_remaining']}/{state['max_bets_per_day']}\n"
        f"Reserve: N{state['reserve']:,.2f}"
    )
