## SM - Persist Resource with Auto-MIME Type v2.0

This brewlytics sub-model persists a web resource and will auto assign the MIME type based on the filename with file type extension. This model will also optionally send a notification of a successful or failed file persistance.

This updated Python script is used process the user-define resource filename and extract the file type extension. Unrecognized file extensions will be persisted as "text/plain" and an MIME Type Error Notification will be sent to the Sub-Model User and the Sub-Model owner. 

Additional file extension-MIME type pairs can be added by editing the embedded table in brewlytics model.

**Resources:**
* [brewlytics Model - SM - Persist Resource with Auto-MIME Type v2.0](https://demo.brewlytics.com/app/#/build/21ee0049-1529-4c29-a2f3-61c3973f3b22)
* [Github Python Script](https://github.com/outsideken/brewlytics/blob/main/submodels/Auto-MIME%20Type.py)
* [Auto-MIME Type CSV (Updated 2022-04-28)](https://github.com/outsideken/brewlytics/blob/main/submodels/Auto-MIME%20Types%20(2022-04-28).csv)

**Embedded Sub-Models:**
* [SM - Github Python Script Fault-Tolerant Hosting](https://demo.brewlytics.com/app/#/build/53b3540c-28e5-4028-e9a6-5426e58f6e55)
* [SM - Persist Resource with Email Notification](https://demo.brewlytics.com/app/#/build/858214aa-0574-48e1-be8a-666efe8445b5)
* [Utility - Get Model Name from Model Id](https://demo.brewlytics.com/app/#/build/92b995d5-cd32-4559-be72-d4d07486a843)
* [Utility - Hormel Email](https://demo.brewlytics.com/app/#/build/defa84ef-b27e-44c2-f999-7f6bcfbde164)

**User-Defined Inputs**
* Parent Model UUID
* Resource
* Resource Name
* Resource UUID
* Resource ACL
* Send MIME Type Error Notification (Boolean)

<hr>

**The following 32 file extensions/26 MIME types are recognized by this sub-model:**

* bmp: image/bmp
* bz: application/x-bzip
* bz2: application/x-bzip2
* csv: text/csv
* dbf: text/plain
* docx: application/vnd.openxmlformats-officedocument.wordprocessingml.document
* gif: image/gif
* gtar: application/x-gtar
* gtz: application/x-compressed
* gz: application/x-gzip
* htm: text/html
* html: text/html
* ico: image/x-icon
* jpe: image/jpeg
* jpeg: image/jpeg
* jpg: image/jpeg
* json: text/json
* kml: application/vnd.google-earth.kml+xml
* kmz: application/vnd.google-earth.kmz
* pdf: application/pdf
* png: image/png
* pptx: application/vnd.openxmlformats-officedocument.presentationml.presentation
* rtf: application/rtf
* shp: x-gis/x-shapefile
* shx: x-gis/x-shapefile
* tar: application/x-tar
* tif: image/tiff
* tiff: image/tiff
* txt: text/plain
* xlsx: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
* z: application/x-compress
* zip: application/zip

<hr>
