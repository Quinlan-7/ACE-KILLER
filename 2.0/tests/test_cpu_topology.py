#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CPU 拓扑模块单元测试 v2.2
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.cpu_topology import (
    get_cpu_brand,
    get_cpu_vendor,
    is_amd_cpu,
    is_intel_cpu,
    get_core_counts,
    get_eco_target_cpus,
    get_eco_affinity_mask,
    get_cpu_summary,
    _logical_to_physical_mapping,
)


class TestCpuTopology(unittest.TestCase):

    def test_brand_and_vendor(self):
        brand = get_cpu_brand()
        vendor = get_cpu_vendor()
        self.assertIsInstance(brand, str)
        self.assertIn(vendor, ("AMD", "Intel", "未知"))
        # 至少一个布尔判定为真（本机必然是 AMD 或 Intel）
        self.assertTrue(is_amd_cpu() or is_intel_cpu())

    def test_core_counts(self):
        physical, logical = get_core_counts()
        self.assertGreaterEqual(physical, 1)
        self.assertGreaterEqual(logical, physical)

    def test_mapping_consistency(self):
        mapping, core_masks = _logical_to_physical_mapping()
        if mapping and core_masks:
            # 每个物理核心掩码内的逻辑 ID 都应映射到对应核心索引
            for idx, mask in enumerate(core_masks):
                for bit in range(64):
                    if mask & (1 << bit):
                        self.assertEqual(mapping.get(bit), idx)

    def test_eco_target(self):
        targets = get_eco_target_cpus()
        self.assertIsInstance(targets, list)
        self.assertGreaterEqual(len(targets), 1)
        # 目标核心必须小于逻辑处理器总数
        _, logical = get_core_counts()
        if logical > 0:
            for t in targets:
                self.assertLess(t, logical)

    def test_eco_affinity_mask(self):
        mask = get_eco_affinity_mask()
        self.assertIsNotNone(mask)
        self.assertIsInstance(mask, int)
        self.assertGreater(mask, 0)

    def test_summary(self):
        summary = get_cpu_summary()
        for key in ("brand", "vendor", "physical_cores", "logical_processors", "eco_target"):
            self.assertIn(key, summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
