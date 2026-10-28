"""Country-level institution coverage; each paper counts once per country."""
from collections import Counter
import copy

def affiliation_counts(papers, theme=None):
    counts = Counter()
    for paper in papers:
        if paper.get('retracted') or (theme and theme not in paper.get('themes', [])):
            continue
        counts.update(set(paper.get('countries', [])))
    return counts

def research_geojson(papers, boundaries, theme=None):
    counts=affiliation_counts(papers,theme)
    result={'type':'FeatureCollection','features':[]}
    for feature in boundaries['features']:
        props=feature['properties']
        code=props.get('ISO_A2_EH') or props.get('ISO_A2')
        if code=='-99':code=props.get('ISO_A2')
        result['features'].append({'type':'Feature','geometry':copy.deepcopy(feature['geometry']),'properties':{'country_code':code,'country_name':props.get('ADMIN') or props.get('NAME'),'papers':counts.get(code,0),'theme':theme or 'all','measure':'Distinct snapshot papers with a listed institution in this country; papers may count in multiple countries.'}})
    return result
