# PeakRetentionTime

A chromatography peak facet that indicates the elapsed time between the injection of the sample and the maximum detector response attributed to the peak (analyte band).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **float** |  | 
**unit** | **str** |  | 

## Example

```python
from openapi_client.models.peak_retention_time import PeakRetentionTime

# TODO update the JSON string below
json = "{}"
# create an instance of PeakRetentionTime from a JSON string
peak_retention_time_instance = PeakRetentionTime.from_json(json)
# print the JSON string representation of the object
print(PeakRetentionTime.to_json())

# convert the object into a dict
peak_retention_time_dict = peak_retention_time_instance.to_dict()
# create an instance of PeakRetentionTime from a dict
peak_retention_time_from_dict = PeakRetentionTime.from_dict(peak_retention_time_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


