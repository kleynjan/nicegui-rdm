from tortoise.models import Model
from tortoise.exceptions import FieldError

class QModel(Model):
    """Extends the standard Tortoise Model; define your own models as QModel subclasses to use with Stores."""

    field_specs = {}    # used by Store to validate and normalize

    @classmethod
    async def create(cls, *args, **kwargs):
        return await super().create(*args, using_db=None, **kwargs)     # because Tortoise type hints suck

    @classmethod
    def get_field_names(cls, join_fields=[]):
        # field_names = cls.describe()["data_fields"]
        # return (["id"] if include_id else []) + [field["name"] for field in field_names] + join_fields
        # perhaps also take a look at self._meta.fields_map.keys()
        return list(cls._meta.fields_db_projection.keys()) + join_fields

    @classmethod
    # {'username': 'CharField', ....}
    def get_field_types(cls) -> list[dict[str, str]]:
        return [{f["name"]: f["field_type"]} for f in cls.describe()["data_fields"]]

    # the missing instance-to-dict function (cf get(). or first().values(*args, **kwargs))
    def values(self, *args, **kwargs) -> dict[str, str | int | bool]:
        # if fields:
        #     return {k: getattr(self, k) for k in fields if not k.startswith("_") and k in fields }
        # return {k: getattr(self, k) for k in self.__dict__ if not k.startswith("_")}

        # copied over from queryset.values()
        # API is instance.values('id', 'name', 'mail', mail='mail_address', tenant='tenant')
        # so allows for selection, renaming and ordering
        if args or kwargs:
            fields_for_select = {}
            for field in args:
                if field in fields_for_select:
                    raise FieldError(f"Duplicate key {field}")
                fields_for_select[field] = field

            for return_as, field in kwargs.items():
                if return_as in fields_for_select:
                    raise FieldError(f"Duplicate key {return_as}")
                fields_for_select[return_as] = field
        else:
            _fields = [
                field
                for field in self._meta.fields_map.keys()
                if field in self._meta.fields_db_projection.keys()
            ]

            fields_for_select = {field: field for field in _fields}

        return {return_as: getattr(self, k) for k, return_as in fields_for_select.items()}
