# DeviceControlDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**device_type** | **str** | A device type is a classification datum that classifies the type of device used. | 
**device_identifier** | **str** | A device identifier is an identifier that identifies some device. | [optional] 
**detection_type** | **str** | A detection type is a classification datum that classifies the type of detection performed by the detector. | [optional] 
**product_manufacturer** | **str** | An equipment manufacturer is a symbol that denotes the entity manufacturing the equipment. | [optional] 
**brand_name** | **str** | A brand name is a marketed name given by a maker of a product to a product or class of products, especially a trademark. | [optional] 
**equipment_serial_number** | **str** | Equipment serial number is measurement metadata that identifies an equipment used in the measuring by its serial number. | [optional] 
**model_number** | **str** | A model number is an information content entity specifically borne by catalogs, design specifications, advertising materials, inventory systems and similar that is about manufactured objects of the same class. | [optional] 
**firmware_version** | **str** | A firmware version is a version number that identifies the firmware of a device. | [optional] 
**detector_offset_setting** | [**DeviceControlDocumentDetectorOffsetSetting**](DeviceControlDocumentDetectorOffsetSetting.md) |  | [optional] 
**detector_sampling_rate_setting** | [**DeviceControlDocumentDetectorSamplingRateSetting**](DeviceControlDocumentDetectorSamplingRateSetting.md) |  | [optional] 

## Example

```python
from openapi_client.models.device_control_document import DeviceControlDocument

# TODO update the JSON string below
json = "{}"
# create an instance of DeviceControlDocument from a JSON string
device_control_document_instance = DeviceControlDocument.from_json(json)
# print the JSON string representation of the object
print(DeviceControlDocument.to_json())

# convert the object into a dict
device_control_document_dict = device_control_document_instance.to_dict()
# create an instance of DeviceControlDocument from a dict
device_control_document_from_dict = DeviceControlDocument.from_dict(device_control_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


