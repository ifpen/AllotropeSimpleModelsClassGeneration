# MeasurementAggregateDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**measurement_document** | [**List[MeasurementDocument]**](MeasurementDocument.md) | A measurement document is a document that encompasses the information associated with a measurement. | 

## Example

```python
from openapi_client.models.measurement_aggregate_document import MeasurementAggregateDocument

# TODO update the JSON string below
json = "{}"
# create an instance of MeasurementAggregateDocument from a JSON string
measurement_aggregate_document_instance = MeasurementAggregateDocument.from_json(json)
# print the JSON string representation of the object
print(MeasurementAggregateDocument.to_json())

# convert the object into a dict
measurement_aggregate_document_dict = measurement_aggregate_document_instance.to_dict()
# create an instance of MeasurementAggregateDocument from a dict
measurement_aggregate_document_from_dict = MeasurementAggregateDocument.from_dict(measurement_aggregate_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


