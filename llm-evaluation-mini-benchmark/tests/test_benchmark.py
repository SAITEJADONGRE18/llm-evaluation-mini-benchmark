import tempfile, unittest
from pathlib import Path
from benchmark import load_benchmark, score_response, evaluate, read_responses_jsonl
class BenchmarkTests(unittest.TestCase):
    def test_unique_items_and_count(self):
        items=load_benchmark(); self.assertEqual(len(items),20); self.assertEqual(len({x['id'] for x in items}),20)
    def test_exact_json_pass(self):
        item=next(x for x in load_benchmark() if x['id']=='IF-01'); self.assertEqual(score_response(item,'{"status":"ok","count":3}')['score'],1.0)
    def test_exact_json_fail(self):
        item=next(x for x in load_benchmark() if x['id']=='IF-01'); self.assertEqual(score_response(item,'Here you go: {"status":"ok","count":3}')['score'],0.0)
    def test_coding_checks(self):
        items={x['id']:x for x in load_benchmark()}; good=score_response(items['CODE-01'],'def is_even(n): return n % 2 == 0'); bad=score_response(items['CODE-01'],'def is_even(n): return True'); self.assertEqual(good['score'],1.0); self.assertLess(bad['score'],1.0)
    def test_missing_response_scores_zero(self):
        ev=evaluate({},'empty'); self.assertEqual(ev['overall_score'],0.0); self.assertEqual(len(ev['missing_ids']),20)
    def test_jsonl_read(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'responses.jsonl'; p.write_text('{"id":"IF-01","response":"ok"}\n',encoding='utf-8'); self.assertEqual(read_responses_jsonl(p),{'IF-01':'ok'})
if __name__=='__main__': unittest.main()
