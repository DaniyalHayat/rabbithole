import json, sys, unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rabbithole.ranker import fit_pairwise, predict
from rabbithole.geo import affiliation_counts, research_geojson

class RankerTests(unittest.TestCase):
    def test_training_reduces_loss(self):
        model=fit_pairwise([[1.,.5],[.4,1.],[1.,1.]],steps=100)
        self.assertLess(model['loss_last'],model['loss_first'])
    def test_correct_pairwise_order(self):
        model=fit_pairwise([[1.,0.],[.7,.1],[1.,.2]],steps=100)
        self.assertGreater(predict(model,[[1.,0.]])[0],predict(model,[[0.,0.]])[0])
    def test_invalid_training_rejected(self):self.assertRaises(ValueError,fit_pairwise,[])
    def test_model_finite(self):
        model=json.loads((ROOT/'outputs/ml_model.json').read_text())
        self.assertTrue(np.isfinite(model['weights']).all());self.assertTrue(np.all(np.array(model['scale'])>0))
    def test_official_test_excluded_from_training_metadata(self):
        model=json.loads((ROOT/'outputs/ml_model.json').read_text())
        self.assertEqual(model['training_queries'],809);self.assertEqual(model['training_pairs'],13785)

class GeographyTests(unittest.TestCase):
    def test_country_counts_unique_per_paper(self):
        self.assertEqual(affiliation_counts([{'countries':['US','US','GB']}]),{'US':1,'GB':1})
    def test_retractions_excluded(self):self.assertFalse(affiliation_counts([{'countries':['US'],'retracted':True}]))
    def test_theme_filter(self):self.assertEqual(affiliation_counts([{'countries':['US'],'themes':['music']},{'countries':['GB'],'themes':['awe']}],'awe'),{'GB':1})
    def test_export_is_geojson_and_preserves_lon_lat(self):
        boundaries={'features':[{'properties':{'ISO_A2_EH':'US','ADMIN':'USA'},'geometry':{'type':'Polygon','coordinates':[[[-100,30],[-90,30],[-100,30]]]}}]}
        out=research_geojson([{'countries':['US']}],boundaries)
        self.assertEqual(out['type'],'FeatureCollection');self.assertEqual(out['features'][0]['properties']['papers'],1);self.assertEqual(out['features'][0]['geometry']['coordinates'][0][0],[-100,30])
    def test_snapshot_geojson_integrity(self):
        geo=json.loads((ROOT/'outputs/research_atlas.geojson').read_text())
        self.assertTrue(all(f['geometry']['type'] in ['Polygon','MultiPolygon'] and f['properties']['papers']>=0 for f in geo['features']))

if __name__=='__main__':unittest.main()
