# PeakPeakWidthAtBaseline

The peak width determined at the baseline level. The peak tangents are drawn from the turning points of the leading and trailing edges. Then the points of intersection with the baseline are calculated. The distance between the two points of intersection is the baseline level width.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **float** |  | 
**unit** | **str** |  | 

## Example

```python
from openapi_client.models.peak_peak_width_at_baseline import PeakPeakWidthAtBaseline

# TODO update the JSON string below
json = "{}"
# create an instance of PeakPeakWidthAtBaseline from a JSON string
peak_peak_width_at_baseline_instance = PeakPeakWidthAtBaseline.from_json(json)
# print the JSON string representation of the object
print(PeakPeakWidthAtBaseline.to_json())

# convert the object into a dict
peak_peak_width_at_baseline_dict = peak_peak_width_at_baseline_instance.to_dict()
# create an instance of PeakPeakWidthAtBaseline from a dict
peak_peak_width_at_baseline_from_dict = PeakPeakWidthAtBaseline.from_dict(peak_peak_width_at_baseline_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


