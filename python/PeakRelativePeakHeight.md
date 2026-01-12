# PeakRelativePeakHeight

A peak facet that denotes the height of the peak relative to some other peak or summation of peaks.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **float** |  | 
**unit** | **str** |  | 

## Example

```python
from openapi_client.models.peak_relative_peak_height import PeakRelativePeakHeight

# TODO update the JSON string below
json = "{}"
# create an instance of PeakRelativePeakHeight from a JSON string
peak_relative_peak_height_instance = PeakRelativePeakHeight.from_json(json)
# print the JSON string representation of the object
print(PeakRelativePeakHeight.to_json())

# convert the object into a dict
peak_relative_peak_height_dict = peak_relative_peak_height_instance.to_dict()
# create an instance of PeakRelativePeakHeight from a dict
peak_relative_peak_height_from_dict = PeakRelativePeakHeight.from_dict(peak_relative_peak_height_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


