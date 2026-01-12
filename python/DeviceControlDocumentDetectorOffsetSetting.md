# DeviceControlDocumentDetectorOffsetSetting

A detector offset setting is a detector setting parameter that adds the specified value to its output signal. It is often used to avoid negative signal values.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **float** |  | 
**unit** | **str** |  | 

## Example

```python
from openapi_client.models.device_control_document_detector_offset_setting import DeviceControlDocumentDetectorOffsetSetting

# TODO update the JSON string below
json = "{}"
# create an instance of DeviceControlDocumentDetectorOffsetSetting from a JSON string
device_control_document_detector_offset_setting_instance = DeviceControlDocumentDetectorOffsetSetting.from_json(json)
# print the JSON string representation of the object
print(DeviceControlDocumentDetectorOffsetSetting.to_json())

# convert the object into a dict
device_control_document_detector_offset_setting_dict = device_control_document_detector_offset_setting_instance.to_dict()
# create an instance of DeviceControlDocumentDetectorOffsetSetting from a dict
device_control_document_detector_offset_setting_from_dict = DeviceControlDocumentDetectorOffsetSetting.from_dict(device_control_document_detector_offset_setting_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


