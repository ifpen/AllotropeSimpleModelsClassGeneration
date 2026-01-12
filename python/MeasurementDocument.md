# MeasurementDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**detection_type** | **str** | A detection type is a classification datum that classifies the type of detection performed by the detector. | [optional] 
**measurement_identifier** | **str** | Measurement id is measurement metadata that identifies the measuring run. | 
**chromatogram_data_cube** | [**ChromatogramDataCube**](ChromatogramDataCube.md) | A chromatogram data cube is a data cube that represents a chromatogram. | 
**chromatography_column_document** | [**ChromatographyColumnDocument**](ChromatographyColumnDocument.md) | A chromatography column document is a document that encompasses the information associated with a chromatography column. | 
**injection_document** | [**InjectionDocument**](InjectionDocument.md) | An injection document is a document that encompasses the information associated with an injection. | 
**device_control_aggregate_document** | [**DeviceControlAggregateDocument**](DeviceControlAggregateDocument.md) | A device control aggregate document is a document that aggregates device control documents. | 
**sample_document** | [**SampleDocument**](SampleDocument.md) | A sample document is a document about a particular sample. | 
**processed_data_aggregate_document** | [**ProcessedDataAggregateDocument**](ProcessedDataAggregateDocument.md) | A processed data aggregate document is a document that aggregates processed data documents. | [optional] 

## Example

```python
from openapi_client.models.measurement_document import MeasurementDocument

# TODO update the JSON string below
json = "{}"
# create an instance of MeasurementDocument from a JSON string
measurement_document_instance = MeasurementDocument.from_json(json)
# print the JSON string representation of the object
print(MeasurementDocument.to_json())

# convert the object into a dict
measurement_document_dict = measurement_document_instance.to_dict()
# create an instance of MeasurementDocument from a dict
measurement_document_from_dict = MeasurementDocument.from_dict(measurement_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


