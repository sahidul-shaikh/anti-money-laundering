"""Deliver the latest passing build run as a pull request, as aml-factory-bot.

Run: uv run python scripts/deliver.py --task T-002 [--phase development]
"""

import argparse

from aml.build.deliver import deliver


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--task", required=True, help="task ID with an intent under tasks/")
    parser.add_argument("--phase", default="development", help="build phase to deliver")
    args = parser.parse_args()
    delivery = deliver(args.task, args.phase)
    print(f"branch  {delivery.branch}")
    print(f"commit  {delivery.commit[:10]}")
    print(f"pr      {delivery.pr_url}")


if __name__ == "__main__":
    main()
