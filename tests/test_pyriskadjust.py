#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `pyriskadjust` package."""


import unittest
import json
from pyriskadjust.models import model_2018_v22


class TestPyriskadjust(unittest.TestCase):
    """Tests for `pyriskadjust` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_model_community_aged_nondual(self):
        self.assertEqual(
            json.dumps(
                model_2018_v22.compute_risk_score_components(
                    ["E1169", "I5030", "I509", "I211", "I209", "R05"], age=70, sex=1
                ),
                sort_keys=True,
                indent=2,
            ),
            json.dumps(
                {
                    "cna_m70_74": 0.379,
                    "cna_hcc88": 0.14,
                    "cna_hcc18": 0.318,
                    "cna_hcc85": 0.323,
                    "cna_hcc85_gdiabetesmellit": 0.154,
                },
                sort_keys=True,
                indent=2,
            ),
        )

    def test_explain_total(self):
        explanation = model_2018_v22.explain_score(
            {
                "cna_m70_74": 0.379,
                "cna_hcc88": 0.14,
                "cna_hcc18": 0.318,
                "cna_hcc85": 0.323,
                "cna_hcc85_gdiabetesmellit": 0.154,
            }
        )
        self.assertEqual(explanation["total"], 1.314)
        self.assertEqual(
            json.dumps(explanation["demographic_components"][0], sort_keys=True),
            json.dumps(
                {
                    "variable_name": "cna_m70_74",
                    "score": 0.379,
                    "description": "Male with age in range 70 to 74",
                },
                sort_keys=True,
            ),
        )
        self.assertEqual(
            json.dumps(explanation["interaction_components"][0], sort_keys=True),
            json.dumps(
                {
                    "variable_name": "cna_hcc85_gdiabetesmellit",
                    "score": 0.154,
                    "description": "Congestive Heart Failure & Diabetes",
                },
                sort_keys=True,
            ),
        )
