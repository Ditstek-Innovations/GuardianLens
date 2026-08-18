# Dataset datasheet — training data of `yolov8n-coco-0.1.0-dev`

**We did not train this model.** This datasheet records what is known about
the upstream training data, honestly including what is *not* known — which is
itself a reason the model cannot pass gate G1 for production.

| Field | Value |
|---|---|
| Dataset | COCO (Common Objects in Context) 2017, the standard benchmark this checkpoint ships pretrained on |
| Contents | ~118k training images, general internet/web photography, 80 object categories, bounding-box labelled |
| Collection provenance | Documented upstream at the dataset level (Flickr-sourced, multi-annotator labelling via Amazon Mechanical Turk) but not to the standard GOVERNANCE.md §9 requires for a site-deployment decision — no consent record, geography or demographic breakdown applicable to *our* sites exists |
| Guardian Lens site data included | **None.** No frame from any Guardian Lens camera, demo or real, was used in training |
| Known gaps | Indoor/office scenes at 640×360 (our dev camera's actual domain) are one slice of a very broad, general-purpose dataset — well represented in aggregate, not validated for our specific cameras; no night/adverse-weather stratification available |

## Consequence

Any accuracy figure carried by this model describes the public COCO
validation split, nothing else. Claims about performance on a Guardian Lens
site — for any of its 80 classes — require labelled footage from that site,
measured per class and per condition. Because this model is general-purpose,
that evaluation burden exists **separately for each class a rule is ever
configured to use**, not once for the model as a whole.
