"""离线单元测试。伪响应只用于接口解析测试，不能充当模型实验记录。"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

spec = importlib.util.spec_from_file_location("dialogue_lab", Path(__file__).with_name("dialogue_lab.py"))
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def response(content, status=200):
    return {"status_code": status, "request_id": "offline-test-only",
            "output": {"choices": [{"message": {"content": content}}]}}


class DialogueTests(unittest.TestCase):
    def test_text_message(self):
        self.assertEqual(lab.build_messages("你好")[0]["content"], "你好")

    def test_empty_question(self):
        with self.assertRaises(lab.LabError):
            lab.build_messages("   ")

    def test_two_image_routes_rejected(self):
        with self.assertRaises(lab.LabError):
            lab.build_messages("你好", "x.png", "一张图")

    def test_caption_is_used(self):
        self.assertIn("红色杯子", lab.build_messages("有几个？", caption="红色杯子")[0]["content"])

    def test_empty_caption(self):
        with self.assertRaises(lab.LabError):
            lab.build_messages("有几个？", caption=" ")

    def test_missing_image(self):
        with self.assertRaises(lab.LabError):
            lab.build_messages("图里是什么", "/file-that-does-not-exist/image.jpg")

    def test_image_with_unicode_and_space(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "中文 图片.png"
            p.write_bytes(b"path-check-only-not-a-model-input")
            content = lab.build_messages("图里是什么", str(p))[0]["content"]
            self.assertEqual(content[0]["image"], p.resolve().as_uri())
            self.assertEqual(content[1]["text"], "图里是什么")

    def test_empty_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.png"
            p.touch()
            with self.assertRaises(lab.LabError):
                lab.existing_file(str(p))

    def test_image_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "file.txt"
            p.write_text("not image")
            with self.assertRaises(lab.LabError):
                lab.build_messages("图里是什么", str(p))

    def test_text_response(self):
        self.assertEqual(lab.extract_answer(response(" 测试文本 ")), "测试文本")

    def test_multimodal_response(self):
        self.assertEqual(lab.extract_answer(response([{"text": "第一段"}, {"image": "ignored"}, {"text": "第二段"}])), "第一段\n第二段")

    def test_non_200_response(self):
        with self.assertRaises(lab.LabError):
            lab.extract_answer(response("不应采纳", 401))

    def test_missing_response_field(self):
        with self.assertRaises(lab.LabError):
            lab.extract_answer({"status_code": 200})

    def test_empty_response(self):
        for content in ("", "   ", [], None, [{"image": "x"}]):
            with self.subTest(content=content), self.assertRaises(lab.LabError):
                lab.extract_answer(response(content))

    def test_read_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "question.txt"
            p.write_text("问题", encoding="utf-8-sig")
            self.assertEqual(lab.read_text(str(p)), "问题")

    def test_empty_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.txt"
            p.write_text(" ")
            with self.assertRaises(lab.LabError):
                lab.read_text(str(p))

    def test_default_does_not_send_or_save(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            p = Path(tmp) / "answer.txt"
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                rc = lab.main(["api", "--model", "offline-test", "--output", str(p)])
            self.assertEqual(rc, 0)
            self.assertIn("CHECK ONLY", buf.getvalue())
            self.assertFalse(p.exists())

    def test_missing_key_exits_without_saving(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            p = Path(tmp) / "answer.txt"
            with contextlib.redirect_stderr(io.StringIO()):
                rc = lab.main(["api", "--model", "offline-test", "--send", "--output", str(p)])
            self.assertEqual(rc, 1)
            self.assertFalse(p.exists())

    def test_bad_endpoint(self):
        for url in ("http://dashscope.aliyuncs.com/api/v1", "https://example.com/api/v1", "https://dashscope.aliyuncs.com/compatible-mode/v1", "https://user:pass@dashscope.aliyuncs.com/api/v1"):
            with self.subTest(url=url), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(lab.main(["api", "--model", "test", "--base-url", url]), 1)

    def test_output_budget(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lab.main(["api", "--model", "test", "--max-tokens", "0"]), 1)

    def test_error_message_redacts_key(self):
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "not-a-real-key"}):
            text = lab.safe_error_message(RuntimeError("not-a-real-key sk-offline-placeholder timeout"))
        self.assertNotIn("not-a-real-key", text)
        self.assertNotIn("sk-offline", text)
        self.assertIn("timeout", text)

    def test_all_exception_paths_redact_key(self):
        for exception in (lab.LabError, OSError, ValueError, RuntimeError, ModuleNotFoundError):
            with self.subTest(exception=exception.__name__), \
                 patch.dict(os.environ, {"DASHSCOPE_API_KEY": "not-a-real-key"}), \
                 patch.object(lab, "run_api", side_effect=exception("request not-a-real-key")), \
                 contextlib.redirect_stderr(io.StringIO()) as buf:
                rc = lab.main(["api", "--model", "offline-only"])
                self.assertEqual(rc, 1)
                self.assertNotIn("not-a-real-key", buf.getvalue())
                self.assertIn("[REDACTED]", buf.getvalue())

    def test_error_message_redacts_bearer_header(self):
        message = lab.safe_error_message(ValueError("Authorization: Bearer test-credential"))
        self.assertNotIn("test-credential", message)

    def test_json_output_rejected_before_send(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            target = Path(tmp) / "answer.json"
            target.write_text("previous record", encoding="utf-8")
            rc = lab.main(["api", "--model", "offline-only", "--output", str(target), "--send"])
            self.assertEqual(rc, 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "previous record")

    def test_input_cannot_be_overwritten_by_answer_or_metadata(self):
        for input_name in ("answer.txt", "answer.json"):
            with self.subTest(input_name=input_name), tempfile.TemporaryDirectory() as tmp, \
                 contextlib.redirect_stderr(io.StringIO()) as buf:
                source = Path(tmp) / input_name
                source.write_text("original question", encoding="utf-8")
                rc = lab.main(["api", "--model", "offline-only", "--question-file", str(source),
                               "--output", str(Path(tmp) / "answer.txt"), "--send"])
                self.assertEqual(rc, 1)
                self.assertIn("与输入文件相同", buf.getvalue())
                self.assertEqual(source.read_text(encoding="utf-8"), "original question")

    def test_tts_cannot_overwrite_reference_audio(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()) as buf:
            text = Path(tmp) / "text.txt"
            text.write_text("offline fixture", encoding="utf-8")
            audio = Path(tmp) / "prompt.wav"
            audio.write_bytes(b"path-test-only")
            rc = lab.main(["tts", "--repo", tmp, "--text-file", str(text),
                           "--prompt-text-file", str(text), "--prompt-wav", str(audio),
                           "--output", str(audio)])
            self.assertEqual(rc, 1)
            self.assertIn("与输入文件相同", buf.getvalue())
            self.assertEqual(audio.read_bytes(), b"path-test-only")

    def test_metadata_directory_rejected_before_writing_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "answer.txt"
            target.with_suffix(".json").mkdir()
            with self.assertRaises(lab.LabError):
                lab.save_text_result("fixture", str(target), "offline_test_fixture", "mock", 0.1)
            self.assertFalse(target.exists())

    def test_empty_model_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lab.main(["api", "--model", " "]), 1)

    def test_bad_camera_index_rejected_before_opening_device(self):
        with patch.dict("sys.modules", {"cv2": None}), \
             contextlib.redirect_stderr(io.StringIO()) as buf:
            self.assertEqual(lab.main(["capture", "--camera", "-1"]), 1)
            self.assertIn("摄像头编号", buf.getvalue())

    def test_send_uses_text_sdk_and_saves(self):
        import types
        fake = types.ModuleType("dashscope")
        fake.Generation = SimpleNamespace(call=Mock(return_value=response("offline fixture")))
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"DASHSCOPE_API_KEY": "not-a-real-key"}, clear=True), patch.dict("sys.modules", {"dashscope": fake}), patch.object(lab.importlib.metadata, "version", return_value="offline-mock"):
            out = Path(tmp) / "answer.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = lab.main(["api", "--model", "test-only", "--output", str(out), "--send"])
            self.assertEqual(rc, 0)
            self.assertEqual(fake.Generation.call.call_count, 1)
            self.assertEqual(fake.Generation.call.call_args.kwargs["result_format"], "message")
            self.assertIn("offline fixture", out.read_text())
            self.assertNotIn("not-a-real-key", out.with_suffix(".json").read_text())
            # 临时文件随测试销毁；这不是对外发布的真实API结果。

    def test_send_uses_image_sdk_with_question_file(self):
        import types
        fake = types.ModuleType("dashscope")
        fake.MultiModalConversation = SimpleNamespace(call=Mock(return_value=response([{"text": "offline fixture"}])))
        pillow = types.ModuleType("PIL")
        pillow.Image = SimpleNamespace(open=MagicMock())
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {"DASHSCOPE_API_KEY": "not-a-real-key"}, clear=True), \
             patch.dict("sys.modules", {"dashscope": fake, "PIL": pillow}), \
             patch.object(lab.importlib.metadata, "version", return_value="offline-mock"):
            photo = Path(tmp) / "中文 图片.png"
            photo.write_bytes(b"mock-image-decoder-only")
            question = Path(tmp) / "question.txt"
            question.write_text("来自语音转写的测试问题", encoding="utf-8")
            target = Path(tmp) / "answer.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = lab.main(["api", "--model", "test-only", "--image", str(photo),
                               "--question-file", str(question), "--output", str(target), "--send"])
            self.assertEqual(rc, 0)
            options = fake.MultiModalConversation.call.call_args.kwargs
            self.assertEqual(options["messages"][0]["content"],
                             [{"image": photo.resolve().as_uri()}, {"text": "来自语音转写的测试问题"}])
            self.assertNotIn("result_format", options)
            pillow.Image.open.return_value.__enter__.return_value.verify.assert_called_once()
            self.assertEqual(target.read_text(encoding="utf-8").strip(), "offline fixture")

    def test_caption_mock_passes_image_and_saves_intermediate_text(self):
        processor = Mock()
        processor.return_value.to.return_value = {"pixel_values": "offline-pixels"}
        processor.decode.return_value = " a cup on a desk "
        model = Mock()
        model.to.return_value.eval.return_value = model
        model.generate.return_value = ["offline-token-ids"]
        torch = SimpleNamespace(inference_mode=MagicMock())
        image = MagicMock()
        image.open.return_value.__enter__.return_value.convert.return_value = "offline-RGB"
        transformers = SimpleNamespace(
            BlipProcessor=SimpleNamespace(from_pretrained=Mock(return_value=processor)),
            BlipForConditionalGeneration=SimpleNamespace(from_pretrained=Mock(return_value=model)))
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict("sys.modules", {"torch": torch, "PIL": SimpleNamespace(Image=image),
                                        "transformers": transformers}):
            photo = Path(tmp) / "scene.png"
            photo.write_bytes(b"mock-input-only")
            output = Path(tmp) / "caption.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = lab.main(["caption", "--image", str(photo), "--output", str(output)])
            self.assertEqual(rc, 0)
            processor.assert_called_once_with(images="offline-RGB", return_tensors="pt")
            model.generate.assert_called_once_with(pixel_values="offline-pixels", max_new_tokens=50)
            self.assertEqual(lab.read_text(str(output)), "a cup on a desk")
            image.open.return_value.__exit__.assert_called_once()

    def test_asr_mock_loads_repo_and_restores_search_path(self):
        for fail in (False, True):
            with self.subTest(inference_fails=fail), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp) / "SenseVoice"
                (repo / "utils").mkdir(parents=True)
                (repo / "model.py").write_text("# mock only", encoding="utf-8")
                (repo / "utils/ctc_alignment.py").write_text("# mock only", encoding="utf-8")
                source = Path(tmp) / "question.wav"
                source.write_bytes(b"mock-audio-only")
                output = Path(tmp) / "question.txt"
                engine = SimpleNamespace(generate=Mock(return_value=[{"text": "raw fixture"}]))
                if fail:
                    engine.generate.side_effect = RuntimeError("mock inference failure")

                def build_model(**kwargs):
                    self.assertEqual(sys.path[0], str(repo.resolve()))
                    self.assertEqual(kwargs["remote_code"], (repo / "model.py").resolve().as_posix())
                    self.assertNotIn("\\", kwargs["remote_code"])
                    return engine

                modules = {"torch": SimpleNamespace(),
                           "funasr": SimpleNamespace(AutoModel=build_model),
                           "funasr.utils.postprocess_utils": SimpleNamespace(
                               rich_transcription_postprocess=lambda value: "识别后的测试问题")}
                previous_path = sys.path[:]
                with patch.dict("sys.modules", modules), contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()):
                    rc = lab.main(["asr", "--repo", str(repo), "--audio", str(source),
                                   "--output", str(output), "--device", "cpu"])
                self.assertEqual(rc, int(fail))
                self.assertEqual(sys.path, previous_path)
                self.assertEqual(engine.generate.call_args.kwargs["input"], str(source.resolve()))
                if fail:
                    self.assertFalse(output.exists())
                else:
                    self.assertEqual(lab.read_text(str(output)), "识别后的测试问题")

    def test_tts_mock_joins_chunks_at_model_rate_and_restores_context(self):
        for fail in (False, True):
            with self.subTest(inference_fails=fail), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp) / "CosyVoice"
                model_dir = repo / "pretrained_models/CosyVoice2-0.5B"
                model_dir.mkdir(parents=True)
                (model_dir / "cosyvoice2.yaml").write_text("mock: only", encoding="utf-8")
                (repo / "third_party/Matcha-TTS/matcha").mkdir(parents=True)
                text = Path(tmp) / "answer.txt"
                text.write_text("测试回答", encoding="utf-8")
                prompt = Path(tmp) / "prompt.txt"
                prompt.write_text("参考音频对应文本", encoding="utf-8")
                audio = Path(tmp) / "prompt.wav"
                audio.write_bytes(b"mock-reference-only")
                output = Path(tmp) / "reply.wav"
                chunks = [MagicMock(), MagicMock()]
                speech = MagicMock()
                speech.numel.return_value = 8
                torch = SimpleNamespace(cat=Mock(return_value=speech),
                                        isfinite=Mock(return_value=SimpleNamespace(all=lambda: True)))
                engine = SimpleNamespace(sample_rate=22050, inference_zero_shot=Mock(
                    return_value=[{"tts_speech": chunk} for chunk in chunks]))
                if fail:
                    engine.inference_zero_shot.side_effect = RuntimeError("mock inference failure")

                def create_engine(**kwargs):
                    self.assertEqual(Path.cwd(), repo.resolve())
                    self.assertEqual(kwargs["model_dir"], str(model_dir.resolve()))
                    return engine

                writer = Mock()
                modules = {"torch": torch, "soundfile": SimpleNamespace(write=writer),
                           "cosyvoice.cli.cosyvoice": SimpleNamespace(AutoModel=create_engine)}
                previous_path, previous_cwd = sys.path[:], Path.cwd()
                with patch.dict("sys.modules", modules), contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()):
                    rc = lab.main(["tts", "--repo", str(repo), "--text-file", str(text),
                                   "--prompt-text-file", str(prompt), "--prompt-wav", str(audio),
                                   "--output", str(output)])
                self.assertEqual(rc, int(fail))
                self.assertEqual(sys.path, previous_path)
                self.assertEqual(Path.cwd(), previous_cwd)
                engine.inference_zero_shot.assert_called_once_with(
                    "测试回答", "参考音频对应文本", str(audio.resolve()), stream=False)
                if fail:
                    writer.assert_not_called()
                else:
                    torch.cat.assert_called_once_with([x.detach().cpu() for x in chunks], dim=1)
                    writer.assert_called_once_with(str(output.resolve()), speech.T.numpy(),
                                                   22050, subtype="PCM_16")

    def test_capture_mock_saves_image_and_always_releases_device(self):
        for failure in (None, "open", "frame", "encode"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                cap = SimpleNamespace(isOpened=Mock(return_value=failure != "open"),
                                      read=Mock(return_value=(failure != "frame", "mock-frame")),
                                      release=Mock())
                cv2 = SimpleNamespace(VideoCapture=Mock(return_value=cap), imencode=Mock(
                    return_value=(failure != "encode", SimpleNamespace(tobytes=lambda: b"mock-image"))))
                output = Path(tmp) / "中文 图片.jpg"
                with patch.dict("sys.modules", {"cv2": cv2}), \
                     contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    rc = lab.main(["capture", "--camera", "0", "--output", str(output)])
                self.assertEqual(rc, int(failure is not None))
                cap.release.assert_called_once()
                if failure:
                    self.assertFalse(output.exists())
                else:
                    self.assertEqual(output.read_bytes(), b"mock-image")
                    cv2.imencode.assert_called_once_with(".jpg", "mock-frame")

    def test_result_record_is_honest(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "record.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                lab.save_text_result("offline fixture", str(p), "offline_test_fixture", "mock", 0.1)
            meta = json.loads(p.with_suffix(".json").read_text())
            self.assertEqual(meta["kind"], "offline_test_fixture")
            self.assertEqual(meta["content_correctness"], "requires_human_review")
            self.assertNotIn("api_key", meta)


if __name__ == "__main__":
    unittest.main(verbosity=2)
