"""相机解析几何及文件检查测试，输入为合成数据；不调用 AnyGrasp。"""
import math
import tempfile
import unittest
from pathlib import Path
import grasp_checks as g


class GeometryTests(unittest.TestCase):
    def test_fov_uses_image_height(self):
        fx, fy, cx, cy = g.intrinsics(960, 720, 90)
        self.assertAlmostEqual(fx, 360)
        self.assertAlmostEqual(fy, 360)
        self.assertEqual((cx, cy), (480, 360))
    def test_invalid_image_size(self):
        for w, h in [(0, 3), (4, -1), (4.5, 3), (True, 3), (math.nan, 3), (math.inf, 3)]:
            with self.subTest(w=w, h=h), self.assertRaises(ValueError):
                g.intrinsics(w, h, 60)
    def test_invalid_fov(self):
        for value in [0, 180, math.nan, math.inf]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                g.intrinsics(640, 480, value)
    def test_depth_endpoints(self):
        self.assertAlmostEqual(g.metric_depth(0, .01, 10), .01)
        self.assertAlmostEqual(g.metric_depth(1, .01, 10), 10)
    def test_depth_roundtrip(self):
        for z in [.1, .3, 2, 8]:
            n, f = .01, 10
            buffer = (f - f*n/z)/(f-n)
            self.assertAlmostEqual(g.metric_depth(buffer, n, f), z)
    def test_invalid_depth_inputs(self):
        for args in [(-.1, .01, 10), (1.1, .01, 10), (.5, 0, 10), (.5, 10, 1), (math.nan, .01, 10)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                g.metric_depth(*args)
    def test_center_projects_forward(self):
        self.assertEqual(g.backproject(320, 240, 1, (500,500,320,240)), (0,0,1))
    def test_cv_image_y_is_down(self):
        self.assertGreater(g.backproject(320, 250, 1, (500,500,320,240))[1], 0)
    def test_backprojection_rejects_zero_depth(self):
        with self.assertRaises(ValueError):
            g.backproject(0, 0, 0, (1,1,0,0))
    def test_identity_view_converts_cv_axes(self):
        view = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]
        self.assertEqual(g.transform_point(g.world_from_camera(view), (1,2,3)), (1,-2,-3))
    def test_nontrivial_view_roundtrip(self):
        # 90 度旋转及非零平移，避免仅用单位矩阵漏掉存储顺序错误。
        view = [[0,-1,0,2],[1,0,0,3],[0,0,1,4],[0,0,0,1]]
        flat = [view[i][j] for j in range(4) for i in range(4)]
        world = g.transform_point(g.world_from_camera(flat), (1,2,3))
        camera_gl = g.transform_point(view, world)
        self.assertEqual(camera_gl, (1,-2,-3))
    def test_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            g.world_from_camera([1]*15)
    def test_rejects_reflection(self):
        with self.assertRaises(ValueError):
            g.validate_rigid([[1,0,0,0],[0,1,0,0],[0,0,-1,0],[0,0,0,1]])
    def test_rejects_nonorthogonal(self):
        with self.assertRaises(ValueError):
            g.validate_rigid([[2,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])


class FileTests(unittest.TestCase):
    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as p:
            self.assertEqual(g.file_state(Path(p)/'absent'), 'MISSING')
    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as p:
            f = Path(p)/'model'; f.touch()
            self.assertEqual(g.file_state(f), 'EMPTY')
    def test_lfs_pointer_is_not_weight(self):
        with tempfile.TemporaryDirectory() as p:
            f = Path(p)/'model'; f.write_bytes(b'version https://git-lfs.github.com/spec/v1\noid sha256:test')
            self.assertEqual(g.file_state(f), 'LFS_POINTER_ONLY')
    def test_presence_does_not_imply_inference(self):
        with tempfile.TemporaryDirectory() as p:
            f = Path(p)/'model'; f.write_bytes(b'fixture')
            self.assertEqual(g.file_state(f), 'PRESENT_NOT_EXECUTED')
    def test_windows_is_not_linux_sdk(self):
        r = g.check_files(None, None, system='Windows')
        self.assertTrue(r['blockers_found'])
        self.assertFalse(r['ready_to_grasp'])
    def test_no_paths_are_not_checked(self):
        r = g.check_files(None, None, system='Linux')
        self.assertTrue(all(x['state']=='NOT_CHECKED' for x in r['checks']))
        self.assertFalse(r['ready_to_grasp'])
    def test_missing_sdk_and_sim_files_block(self):
        with tempfile.TemporaryDirectory() as p:
            r = g.check_files(Path(p), Path(p), system='Linux')
            self.assertTrue(r['blockers_found'])
            self.assertEqual(r['sdk_inference'], 'NOT_RUN')
    def test_new_demo_checks_segmentation_input(self):
        with tempfile.TemporaryDirectory() as p:
            d = Path(p)/'grasp_detection'; d.mkdir()
            (d/'demo.py').write_text("read('seg_mask.png')")
            r = g.check_files(Path(p), None, system='Linux')
            self.assertTrue(any(x['item'].endswith('seg_mask.png') for x in r['checks']))
    def test_empty_loaded_binary_is_not_presence(self):
        with tempfile.TemporaryDirectory() as p:
            d = Path(p); (d/'gsnet.so').touch()
            self.assertEqual(g.binary_state(d, '.cpython-39-x86_64-linux-gnu.so'), 'EMPTY')
    def test_lfs_loaded_binary_is_not_presence(self):
        with tempfile.TemporaryDirectory() as p:
            d = Path(p)
            (d/'gsnet.so').write_bytes(b'version https://git-lfs.github.com/spec/v1\n')
            self.assertEqual(g.binary_state(d, '.cpython-39-x86_64-linux-gnu.so'), 'LFS_POINTER_ONLY')
    def test_same_python_wrong_architecture_does_not_match(self):
        with tempfile.TemporaryDirectory() as p:
            d = Path(p); versions = d/'gsnet_versions'; versions.mkdir()
            (versions/'gsnet.cpython-39-aarch64-linux-gnu.so').write_bytes(b'fixture')
            self.assertEqual(g.binary_state(d, '.cpython-39-x86_64-linux-gnu.so'), 'MISSING')
    def test_same_architecture_wrong_python_does_not_match(self):
        with tempfile.TemporaryDirectory() as p:
            d = Path(p); versions = d/'gsnet_versions'; versions.mkdir()
            (versions/'gsnet.cpython-310-x86_64-linux-gnu.so').write_bytes(b'fixture')
            self.assertEqual(g.binary_state(d, '.cpython-39-x86_64-linux-gnu.so'), 'MISSING')
    def test_matching_source_still_needs_copy(self):
        with tempfile.TemporaryDirectory() as p:
            root = Path(p); d = root/'grasp_detection'; d.mkdir()
            versions = d/'gsnet_versions'; versions.mkdir()
            suffix = '.cpython-39-x86_64-linux-gnu.so'
            (versions/('gsnet'+suffix)).write_bytes(b'fixture')
            r = g.check_files(root, None, system='Linux', extension_suffix=suffix)
            self.assertTrue(any(x['state']=='MATCHING_NAME_NOT_LOADED' for x in r['checks']))
            self.assertTrue(r['blockers_found'])
            self.assertFalse(r['ready_to_grasp'])
    def test_copied_binary_never_claims_abi_compatible(self):
        with tempfile.TemporaryDirectory() as p:
            d = Path(p); (d/'gsnet.so').write_bytes(b'fixture')
            self.assertEqual(g.binary_state(d, '.cpython-39-x86_64-linux-gnu.so'), 'PRESENT_ABI_NOT_VALIDATED')
    def test_license_config_alone_does_not_complete_package(self):
        with tempfile.TemporaryDirectory() as p:
            root = Path(p); license_dir = root/'grasp_detection'/'license'
            license_dir.mkdir(parents=True)
            (license_dir/'licenseCfg.json').write_text('{}')
            r = g.check_files(root, None, system='Linux')
            for suffix in ('*.public_key', '*.signature', '*.lic'):
                with self.subTest(suffix=suffix):
                    self.assertTrue(any(x['item'].endswith(suffix) and x['state']=='MISSING'
                                        for x in r['checks']))
    def test_empty_license_part_is_reported(self):
        with tempfile.TemporaryDirectory() as p:
            d = Path(p); (d/'fixture.signature').touch()
            self.assertEqual(g.license_part_state(d, '*.signature'), 'EMPTY')


if __name__ == '__main__':
    unittest.main(verbosity=2)
