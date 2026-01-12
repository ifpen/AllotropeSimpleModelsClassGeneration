# PeakPeakSelectivityChromatography

A chromatography peak facet that denotes the ratio of the peak's capacity factor to that of another specified peak.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **float** |  | 
**unit** | **str** |  | 

## Example

```python
from openapi_client.models.peak_peak_selectivity_chromatography import PeakPeakSelectivityChromatography

# TODO update the JSON string below
json = "{}"
# create an instance of PeakPeakSelectivityChromatography from a JSON string
peak_peak_selectivity_chromatography_instance = PeakPeakSelectivityChromatography.from_json(json)
# print the JSON string representation of the object
print(PeakPeakSelectivityChromatography.to_json())

# convert the object into a dict
peak_peak_selectivity_chromatography_dict = peak_peak_selectivity_chromatography_instance.to_dict()
# create an instance of PeakPeakSelectivityChromatography from a dict
peak_peak_selectivity_chromatography_from_dict = PeakPeakSelectivityChromatography.from_dict(peak_peak_selectivity_chromatography_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


