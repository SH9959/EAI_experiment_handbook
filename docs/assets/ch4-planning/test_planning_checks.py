"""合成元数据、假控制器上的逻辑测试；不启动 Unity 或模型。"""
import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import planning_checks as p
import ai2thor_checked_demo as demo


class ActionTests(unittest.TestCase):
    def test_normal_action(self):
        self.assertEqual(p.parse_action('GotoObject-Cup'), ('GotoObject','Cup'))
    def test_case_is_canonical(self):
        self.assertEqual(p.parse_action(' pickupobject-Cup '), ('PickupObject','Cup'))
    def test_negative_coordinates_not_truncated(self):
        self.assertEqual(p.parse_action('PickupObject-Cup|-01.1|+00.5|-02.0')[1], 'Cup|-01.1|+00.5|-02.0')
    def test_done_exact(self):
        self.assertEqual(p.parse_action('done'), ('Done',None))
    def test_done_with_target_rejected(self):
        with self.assertRaises(ValueError): p.parse_action('Done-Cup')
    def test_done_substring_not_stop(self):
        self.assertEqual(p.parse_action('GotoObject-UndoneObject')[0], 'GotoObject')
    def test_unknown_method_rejected(self):
        for s in ['reset-Cup', 'TeleportObject-Cup', '__getattribute__-Cup']:
            with self.subTest(s=s), self.assertRaises(ValueError): p.parse_action(s)
    def test_multi_command_rejected(self):
        for s in ['GotoObject-Cup\nDone', 'GotoObject-Cup;Done', '```Done```']:
            with self.subTest(s=s), self.assertRaises(ValueError): p.parse_action(s)
    def test_missing_target_rejected(self):
        for s in ['', 'PickupObject', 'PickupObject-']:
            with self.subTest(s=s), self.assertRaises(ValueError): p.parse_action(s)
    def test_exact_type_not_substring(self):
        objs=[{'objectId':'ButterKnife|1','objectType':'ButterKnife'}]
        with self.assertRaises(ValueError): p.find_object(objs,'Knife')
    def test_exact_id_not_nearest_other(self):
        objs=[{'objectId':'Cup|1','objectType':'Cup'},{'objectId':'Cup|2','objectType':'Cup'}]
        self.assertEqual(p.find_object(objs,'Cup|2')['objectId'],'Cup|2')
    def test_ambiguous_type_rejected(self):
        objs=[{'objectId':'Cup|1','objectType':'Cup'},{'objectId':'Cup|2','objectType':'Cup'}]
        with self.assertRaises(ValueError): p.find_object(objs,'Cup')
    def test_false_feedback_not_lost(self):
        self.assertEqual(p.action_feedback({'lastActionSuccess':False,'errorMessage':'blocked'}),(False,'blocked'))
    def test_missing_feedback_not_success(self):
        for x in [None,'False',0]:
            with self.subTest(x=x), self.assertRaises(ValueError): p.action_feedback({'lastActionSuccess':x})
    def test_duplicate_skills_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'action.json'; path.write_text('[{"name":"Done"},{"name":"done"}]')
            with self.assertRaises(ValueError): p.supported_actions(path)
    def test_custom_skill_table_cannot_allow_controller_methods(self):
        with self.assertRaises(ValueError): p.parse_action('reset-Cup', ('reset',))
        self.assertEqual(p.parse_action('done', ('done',)), ('Done', None))
    def test_exact_id_without_coordinates(self):
        objs=[{'objectId':'spawned_cup_1','objectType':'Cup'}]
        self.assertEqual(p.find_object(objs,'spawned_cup_1')['objectId'],'spawned_cup_1')
    def test_malformed_object_list_is_explicit_failure(self):
        for objs in (None, [None], {}):
            with self.subTest(objs=objs), self.assertRaises(ValueError): p.find_object(objs,'Cup')


class VirtualHomeTests(unittest.TestCase):
    def setUp(self):
        self.graph={'nodes':[{'id':7,'class_name':'salmon','states':[]},
                             {'id':25,'class_name':'fridge','states':['CLOSED']}], 'edges':[]}
    def test_plan_uses_graph_ids(self):
        script=p.virtualhome_plan(self.graph)
        self.assertIn('<char0> [PUTIN] <salmon> (7) <fridge> (25)',script)
        self.assertEqual(len(script),6)
    def test_already_open_fridge(self):
        self.graph['nodes'][1]['states']=['OPEN']
        self.assertFalse(any('[OPEN]' in x for x in p.virtualhome_plan(self.graph)))
    def test_cereal_not_substituted_for_salmon(self):
        self.graph['nodes'][0]['class_name']='cereal'
        with self.assertRaises(ValueError): p.virtualhome_plan(self.graph)
    def test_duplicate_nodes(self):
        self.graph['nodes'][1]['id']=7
        with self.assertRaises(ValueError): p.virtualhome_plan(self.graph)
    def test_unknown_fridge_state(self):
        self.graph['nodes'][1]['states']=[]
        with self.assertRaises(ValueError): p.virtualhome_plan(self.graph)
    def test_missing_edge_is_not_success(self):
        self.assertFalse(p.inside_relation(self.graph,7,25))
    def test_reverse_edge_is_not_success(self):
        self.graph['edges']=[{'from_id':25,'to_id':7,'relation_type':'INSIDE'}]
        self.assertFalse(p.inside_relation(self.graph,7,25))
    def test_inside_edge_checked(self):
        self.graph['edges']=[{'from_id':7,'to_id':25,'relation_type':'INSIDE'}]
        self.assertTrue(p.inside_relation(self.graph,7,25))
    def test_missing_edges_unknown(self):
        del self.graph['edges']
        with self.assertRaises(ValueError): p.inside_relation(self.graph,7,25)
    def test_conflicting_fridge_state_rejected(self):
        self.graph['nodes'][1]['states']=['OPEN','CLOSED']
        with self.assertRaises(ValueError): p.virtualhome_plan(self.graph)


class FakeCourseController:
    def __init__(self):
        self.calls=[]
        self.last_event=SimpleNamespace(metadata={'objects':[{'objectId':'Cup|1','objectType':'Cup','pickupable':True,'receptacle':False}]})
    def _genAI2ThorAPI(self, action, target): return {'action':action,'objectId':target}, ''
    def step(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(metadata={'lastActionSuccess':True,'errorMessage':''})


class ControllerTests(unittest.TestCase):
    def setUp(self): self.c=demo.checked_controller(FakeCourseController)()
    def test_done_never_dispatched(self):
        with self.assertRaises(ValueError): self.c.execute_checked('Done',p.COURSE_SKILLS)
        self.assertEqual(self.c.calls,[])
    def test_put_uses_receptacle(self):
        with self.assertRaises(ValueError): self.c.execute_checked('PutObject-Cup',p.COURSE_SKILLS)
        self.assertEqual(self.c.calls,[])
    def test_missing_object_not_index_error(self):
        with self.assertRaises(ValueError): self.c.execute_checked('GotoObject-Knife',p.COURSE_SKILLS)
    def test_valid_pick_uses_full_id(self):
        _,ok,_=self.c.execute_checked('PickupObject-Cup',p.COURSE_SKILLS)
        self.assertTrue(ok)
        self.assertEqual(self.c.calls[0]['objectId'],'Cup|1')
    def test_empty_pose_is_handled(self):
        self.c.step=lambda **kwargs: SimpleNamespace(metadata={'lastActionSuccess':True,'actionReturn':[]})
        with self.assertRaises(ValueError): self.c._getTeleportPose({'objectId':'Cup|1'})
    def test_response_text(self):
        r=SimpleNamespace(status_code=200,output=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=[{'text':'Done'}]))]))
        self.assertEqual(demo.response_text(r),'Done')
    def test_non200_response_rejected(self):
        with self.assertRaises(ValueError): demo.response_text(SimpleNamespace(status_code=403))
    def test_wrong_source_not_loaded(self):
        with tempfile.TemporaryDirectory() as d:
            for f in demo.SOURCE_BLOBS: (Path(d)/f).write_text('not the checked source')
            with self.assertRaises(ValueError): demo.check_source(Path(d))
    def test_source_hash_allows_crlf_without_allowing_content_change(self):
        raw=b'line one\nline two\n'
        expected=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
        with tempfile.TemporaryDirectory() as d, patch.dict(demo.SOURCE_BLOBS, {'source.py':expected}, clear=True):
            path=Path(d)/'source.py'
            path.write_bytes(raw.replace(b'\n',b'\r\n'))
            demo.check_source(Path(d))
            path.write_bytes(raw+b'changed')
            with self.assertRaises(ValueError): demo.check_source(Path(d))
    def test_invalid_pose_values_not_sent_to_teleport(self):
        for invalid in (float('nan'),float('inf'),'0',True):
            with self.subTest(invalid=invalid):
                pose={'x':invalid,'y':0.0,'z':0.0,'rotation':0.0,'horizon':0.0}
                self.c.step=lambda **kwargs: SimpleNamespace(metadata={'lastActionSuccess':True,'actionReturn':[pose]})
                with self.assertRaises(ValueError):
                    self.c._getTeleportPose({'objectId':'Cup|1','position':{'x':0.0,'y':0.0,'z':0.0}})
    def test_response_dict_and_missing_or_empty_fields(self):
        valid={'status_code':200,'output':{'choices':[{'message':{'content':'Done'}}]}}
        self.assertEqual(demo.response_text(valid),'Done')
        for response in ({'status_code':200}, {'status_code':200,'output':{'choices':[]}},
                         {'status_code':200,'output':{'choices':[{'message':{'content':[{'text':None}]}}]}}):
            with self.subTest(response=response), self.assertRaises(ValueError): demo.response_text(response)


class MainLoopTests(unittest.TestCase):
    """只替身执行主循环；任何 --run/--send 均不会触及真实仿真器或 SDK。"""
    def fake_run(self, inputs, *, metadata=None, step_error=False, snapshot_error=False, llm_actions=None, extra=()):
        created=[]
        class FakeController(FakeCourseController):
            def __init__(self, **kwargs):
                super().__init__()
                self.last_event.frame=None
                self.stopped=False
                created.append(self)
            def reset(self, scene): return self.last_event
            def step(self, **kwargs):
                self.calls.append(kwargs)
                if step_error: raise ValueError('mock transport failure')
                result={'lastActionSuccess':True,'errorMessage':''} if metadata is None else metadata
                self.last_event=SimpleNamespace(metadata={'objects':self.last_event.metadata['objects'],**result},frame=None)
                return self.last_event
            def stop(self): self.stopped=True
        course=SimpleNamespace(MyController=FakeController,get_prompt=Mock(return_value='offline prompt'),
                               get_all_objects_in_scene=lambda event:['Cup'])
        loader=SimpleNamespace(exec_module=lambda module:None)
        saved=[]
        def save_image(path):
            if snapshot_error and saved: raise ValueError('mock snapshot failure')
            saved.append(str(path))
            Path(path).write_bytes(b'MOCK-NOT-A-REAL-IMAGE')
        pillow=SimpleNamespace(Image=SimpleNamespace(fromarray=lambda frame:SimpleNamespace(save=save_image)))
        response_call=Mock(side_effect=[{'status_code':200,'output':{'choices':[{'message':{'content':x}}]}}
                                       for x in (llm_actions or [])])
        sdk=SimpleNamespace(MultiModalConversation=SimpleNamespace(call=response_call))
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            (directory/'action.json').write_text(json.dumps([{'name':x} for x in p.COURSE_SKILLS]),encoding='utf-8')
            args=['--course-dir',tmp,'--output',str(directory/'runs'),'--run',*extra]
            if llm_actions is not None: args+=['--mode','llm','--send']
            with patch.object(demo,'check_source'), \
                 patch.object(demo.importlib.util,'spec_from_file_location',return_value=SimpleNamespace(loader=loader)), \
                 patch.object(demo.importlib.util,'module_from_spec',return_value=course), \
                 patch.dict('sys.modules',{'PIL':pillow,'dashscope':sdk}), \
                 patch.dict(os.environ,{'DASHSCOPE_API_KEY':'offline-test-key'},clear=True), \
                 patch('builtins.input',side_effect=inputs), contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                rc=demo.main(args)
            files=list((directory/'runs').glob('*/run.json'))
            record=json.loads(files[0].read_text(encoding='utf-8')) if files else None
        return rc,record,created,response_call,course
    def test_manual_done_records_stop_without_dispatch_or_success(self):
        rc,record,controllers,call,_=self.fake_run(['Done'])
        self.assertEqual(rc,0)
        self.assertEqual(record['stop_reason'],'USER_DONE')
        self.assertEqual(record['task_success'],'NOT_EVALUATED')
        self.assertEqual(controllers[0].calls,[])
        self.assertTrue(controllers[0].stopped)
        call.assert_not_called()
    def test_invalid_action_is_recorded_before_next_input(self):
        rc,record,controllers,_,_=self.fake_run(['reset-Cup','Done'])
        self.assertEqual(rc,0)
        self.assertEqual(record['steps'][0]['action'],'reset-Cup')
        self.assertFalse(record['steps'][0]['executed'])
        self.assertEqual(controllers[0].calls,[])
    def test_failed_action_is_executed_but_not_successful(self):
        rc,record,controllers,_,_=self.fake_run(['PickupObject-Cup','Done'],metadata={'lastActionSuccess':False,'errorMessage':'blocked'})
        self.assertEqual(rc,0)
        self.assertTrue(record['steps'][0]['executed'])
        self.assertFalse(record['steps'][0]['lastActionSuccess'])
        self.assertEqual(record['steps'][0]['feedback'],'blocked')
        self.assertTrue(controllers[0].stopped)
    def test_missing_feedback_does_not_claim_action_was_unexecuted(self):
        rc,record,controllers,_,_=self.fake_run(['PickupObject-Cup'],metadata={})
        self.assertEqual(rc,2)
        self.assertEqual(record['stop_reason'],'ACTION_OUTCOME_UNKNOWN')
        self.assertTrue(record['steps'][0]['executed'])
        self.assertIsNone(record['steps'][0]['lastActionSuccess'])
        self.assertTrue(controllers[0].stopped)
    def test_transport_failure_execution_status_is_unknown(self):
        rc,record,controllers,_,_=self.fake_run(['PickupObject-Cup'],step_error=True)
        self.assertEqual(rc,2)
        self.assertIsNone(record['steps'][0]['executed'])
        self.assertEqual(record['task_success'],'NOT_EVALUATED')
        self.assertTrue(controllers[0].stopped)
    def test_snapshot_failure_does_not_duplicate_or_reclassify_action(self):
        rc,record,controllers,_,_=self.fake_run(['PickupObject-Cup'],snapshot_error=True)
        self.assertEqual(rc,2)
        self.assertEqual(len(record['steps']),1)
        self.assertTrue(record['steps'][0]['executed'])
        self.assertTrue(record['steps'][0]['lastActionSuccess'])
        self.assertTrue(controllers[0].stopped)
    def test_llm_next_prompt_receives_actual_failure_feedback(self):
        rc,record,controllers,call,course=self.fake_run(['',''],metadata={'lastActionSuccess':False,'errorMessage':'blocked'},
                                                       llm_actions=['PickupObject-Cup','Done'])
        self.assertEqual(rc,0)
        self.assertEqual(call.call_count,2)
        self.assertEqual(course.get_prompt.call_args.kwargs['feed_back_message'],'blocked')
        self.assertEqual(record['stop_reason'],'MODEL_DONE')
        self.assertEqual(record['task_success'],'NOT_EVALUATED')
        self.assertTrue(controllers[0].stopped)
    def test_llm_without_send_does_not_start_simulator(self):
        rc,record,controllers,call,_=self.fake_run([],extra=['--mode','llm'])
        self.assertEqual(rc,2)
        self.assertIsNone(record)
        self.assertEqual(controllers,[])
        call.assert_not_called()


if __name__=='__main__':
    unittest.main(verbosity=2)
