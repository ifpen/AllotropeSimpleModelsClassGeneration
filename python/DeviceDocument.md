# DeviceDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**device_type** | **str** | A device type is a classification datum that classifies the type of device used. | 
**device_identifier** | **str** | A device identifier is an identifier that identifies some device. | [optional] 
**model_number** | **str** | A model number is an information content entity specifically borne by catalogs, design specifications, advertising materials, inventory systems and similar that is about manufactured objects of the same class. | [optional] 
**product_manufacturer** | **str** | An equipment manufacturer is a symbol that denotes the entity manufacturing the equipment. | [optional] 
**brand_name** | **str** | A brand name is a marketed name given by a maker of a product to a product or class of products, especially a trademark. | [optional] 
**equipment_serial_number** | **str** | Equipment serial number is measurement metadata that identifies an equipment used in the measuring by its serial number. | [optional] 
**firmware_version** | **str** | A firmware version is a version number that identifies the firmware of a device. | [optional] 

## Example

```python
from openapi_client.models.device_document import DeviceDocument

# TODO update the JSON string below
json = "{}"
# create an instance of DeviceDocument from a JSON string
device_document_instance = DeviceDocument.from_json(json)
# print the JSON string representation of the object
print(DeviceDocument.to_json())

# convert the object into a dict
device_document_dict = device_document_instance.to_dict()
# create an instance of DeviceDocument from a dict
device_document_from_dict = DeviceDocument.from_dict(device_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


