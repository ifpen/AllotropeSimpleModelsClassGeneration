# GasChromatographyDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**analyst** | **str** | Analyst is measurement metadata about the name or identifier of a person that has the role of an analyst in the measurement. | 
**submitter** | **str** | Submitter is measurement metadata about the name or identifier of a person that has the role of a submitter in the measurement. | [optional] 
**device_method_identifier** | **str** | A device method identifier is an identifier that identifies the device method used in a measurement. | 
**measurement_aggregate_document** | [**MeasurementAggregateDocument**](MeasurementAggregateDocument.md) | A measurement aggregate document is a document about a collection of measurement documents. | 
**diagnostic_trace_aggregate_document** | [**DiagnosticTraceAggregateDocument**](DiagnosticTraceAggregateDocument.md) | A diagnostic trace aggregate document is a document that aggregates diagnostic trace documents. | [optional] 

## Example

```python
from openapi_client.models.gas_chromatography_document import GasChromatographyDocument

# TODO update the JSON string below
json = "{}"
# create an instance of GasChromatographyDocument from a JSON string
gas_chromatography_document_instance = GasChromatographyDocument.from_json(json)
# print the JSON string representation of the object
print(GasChromatographyDocument.to_json())

# convert the object into a dict
gas_chromatography_document_dict = gas_chromatography_document_instance.to_dict()
# create an instance of GasChromatographyDocument from a dict
gas_chromatography_document_from_dict = GasChromatographyDocument.from_dict(gas_chromatography_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


