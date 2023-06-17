# CurrentBannerWatcher
Automated data process script to cache Genshin Impact wish event details

This is a supporting repository for [Snap.Hutao](https://github.com/DGP-Studio/Snap.Hutao) Metadata

## Data Structure
```JSON
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",
  "properties": {
    "banner-ann-id": {
      "type": "object",
      "properties": {
        "zh-cn": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "en-us": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "zh-tw": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "ja": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "ko": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "es": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "fr": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "ru": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "th": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "vi": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "de": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "id": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "pt": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "tr": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "it": {
          "type": "object",
          "properties": {
            "banner_image": {
              "type": "string"
            },
            "banner_subtitle": {
              "type": "string"
            }
          },
          "required": [
            "banner_image",
            "banner_subtitle"
          ]
        },
        "five_star_item_1": {
          "type": "integer"
        },
        "five_star_item_2": {
          "type": "integer"
        },
        "four_star_item_1": {
          "type": "integer"
        },
        "four_star_item_2": {
          "type": "integer"
        },
        "four_star_item_3": {
          "type": "integer"
        },
        "four_star_item_4": {
          "type": "integer"
        }
        "four_star_item_5": {
          "type": "integer"
        }
      },
      "required": [
        "zh-cn",
        "en-us",
        "zh-tw",
        "ja",
        "ko",
        "es",
        "fr",
        "ru",
        "th",
        "vi",
        "de",
        "id",
        "pt",
        "tr",
        "it",
        "five_star_item_1",
        "four_star_item_1",
        "four_star_item_2",
        "four_star_item_3",
        "four_star_item_4"
      ]
    }
  },
  "required": [
    "banner-ann-id"
  ]
}
```
