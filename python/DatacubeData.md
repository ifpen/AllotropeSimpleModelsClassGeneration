# DatacubeData


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**dimensions** | **List[List[float]]** |  | [optional] 
**measures** | **List[List[float]]** |  | [optional] 

## Example

```python
from openapi_client.models.datacube_data import DatacubeData

# TODO update the JSON string below
json = "{}"
# create an instance of DatacubeData from a JSON string
datacube_data_instance = DatacubeData.from_json(json)
# print the JSON string representation of the object
print(DatacubeData.to_json())

# convert the object into a dict
datacube_data_dict = datacube_data_instance.to_dict()
# create an instance of DatacubeData from a dict
datacube_data_from_dict = DatacubeData.from_dict(datacube_data_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


