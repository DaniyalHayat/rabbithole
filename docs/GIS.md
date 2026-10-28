# Research atlas and ArcGIS access

I added a country-level research atlas using institution-country metadata supplied with the OpenAlex authorships. It can show all eight threads or one thread and export a standards-based WGS84 GeoJSON FeatureCollection for inspection in GIS tools.

The browser atlas and Python GeoJSON build are free to run and do not require Esri software, an Esri account, or an API key. The export is ArcGIS-compatible data; I do not claim that the app was developed in ArcGIS or that ArcPy was executed.

## What the counts mean

- Each non-retracted paper counts once per country listed in its institution affiliations.
- Multiple authors or institutions in one country do not multiply a paper's country count.
- An international collaboration can contribute one paper to several countries. Country counts are not additive to the corpus total.
- Missing affiliations remain missing. An affiliation country is not an author's nationality or identity.
- The corpus is a small English-language convenience sample. The map is not a national research ranking or a measure of scientific quality.
- Natural Earth's generalized 1:110m boundaries omit some small territories. A country's button can still show its papers even when no polygon is available at this scale.

## Esri licensing check — October 27, 2026

- [ArcGIS Online](https://doc.arcgis.com/en/arcgis-online/reference/faq.htm) offers a free public account for personal, noncommercial use with limited features.
- [ArcGIS Pro](https://developers.arcgis.com/documentation/portal-and-data-services/tools/arcgis-pro/) offers a 21-day trial; it is not permanently free desktop software.
- [ArcPy](https://support.esri.com/en-us/knowledge-base/faq-can-arcpy-be-used-without-installing-arcgis-pro-000032656) requires a licensed ArcGIS installation, such as Pro or Server. Installing a Python package alone does not supply that license.

I kept the project independent of that licensing. Open `outputs/research_atlas.geojson` in a GIS application that supports GeoJSON, or use the browser's Export GeoJSON button to export the selected thread. Esri feature availability depends on the account type; an exported compatible file does not promise that hosted feature publishing is available on a free public account.

## Boundary attribution

Made with [Natural Earth](https://www.naturalearthdata.com/), whose map data is [public domain](https://www.naturalearthdata.com/about/terms-of-use/). The source boundary file and SHA-256 manifest are checked in. Coordinates are WGS84 longitude/latitude. No address-level locations or inferred personal locations are collected.
