from __future__ import annotations

import argparse

from majiang_support.core.hand import Hand
from majiang_support.core.tile import parse_suit
from majiang_support.strategy.discard import recommend_discard


def main() -> None:
    parser = argparse.ArgumentParser(prog="majiang")
    subparsers = parser.add_subparsers(dest="command", required=True)

    recommend = subparsers.add_parser("recommend", help="Recommend a discard for a hand.")
    recommend.add_argument("--hand", required=True, help='Example: "1m 2m 3m 5m 6m 8m 8m 2p 3p 4p 6s 7s 9s 9s"')
    recommend.add_argument("--missing", help="Missing suit: m, p, s, 万, 筒, 条")

    args = parser.parse_args()

    if args.command == "recommend":
        hand = Hand.parse(args.hand)
        missing_suit = parse_suit(args.missing)
        recommendation = recommend_discard(hand, missing_suit)

        print(f"推荐出牌：{recommendation.best.tile.label}")
        if recommendation.missing_suit_active:
            print("定缺状态：手里仍有缺门牌，候选已限制在缺门内")

        print()
        print("候选评分：")
        for candidate in recommendation.candidates:
            effective = ",".join(candidate.effective.labels) or "-"
            print(
                f"{candidate.tile.label}\t"
                f"score={candidate.score}\t"
                f"shanten={candidate.shanten}\t"
                f"effective={candidate.effective.remaining_total}\t"
                f"structure={candidate.structure_score}\t"
                f"tiles={effective}"
            )

        print()
        print("推荐理由：")
        for index, reason in enumerate(recommendation.best.reasons, start=1):
            print(f"{index}. {reason}")


if __name__ == "__main__":
    main()

