#!/usr/bin/env python3
"""验证固定语义评审与 transcript 的哈希绑定。"""

from __future__ import annotations

import unittest

from grade_semantic_rubric import REVIEWS, transcript_hash, validate_review_binding


class SemanticRubricTests(unittest.TestCase):
    def test_matching_hash_passes(self) -> None:
        transcript = "固定 transcript\n"
        review = {"transcript_sha256": transcript_hash(transcript)}

        self.assertEqual(
            transcript_hash(transcript),
            validate_review_binding(1, "with_skill", transcript, review),
        )

    def test_changed_transcript_requires_new_review(self) -> None:
        review = {"transcript_sha256": transcript_hash("原始 transcript\n")}

        with self.assertRaisesRegex(ValueError, "必须重新进行语义评审"):
            validate_review_binding(1, "with_skill", "已修改 transcript\n", review)

    def test_every_fixed_review_has_sha256(self) -> None:
        for key, review in REVIEWS.items():
            with self.subTest(review=key):
                digest = review.get("transcript_sha256")
                self.assertIsInstance(digest, str)
                self.assertRegex(digest, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
