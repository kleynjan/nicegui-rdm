from tortoise.models import Model
from tortoise.exceptions import FieldError

from .types import FieldSpec, Validator

required_validator = Validator(
    message="This field is required",
    validator=lambda v, _: v is not None
)

class QModel(Model):
    """Extends the standard Tortoise Model; define your own models as QModel subclasses to use with Stores."""

    field_specs: dict[str, FieldSpec] = {}

    @classmethod
    def get_all_field_specs(cls) -> dict[str, FieldSpec]:
        """Return field_specs merged with auto-generated required validators.

        Auto-generates a 'required' validator for every non-nullable
        CharField/TextField that doesn't already have an explicit field_spec.
        Requires Tortoise metadata to be initialized.
        """
        specs = dict(cls.field_specs)
        for name, field in cls._meta.fields_map.items():
            if name in specs or name == 'id':
                continue
            if getattr(field, 'pk', False) or getattr(field, 'auto_now_add', False):
                continue
            if getattr(field, 'null', False) or getattr(field, 'generated', False):
                continue
            if field.__class__.__name__ in ('CharField', 'TextField'):
                specs[name] = FieldSpec(validators=[required_validator])
        return specs

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
    def _get_fk_source_field(cls, field_name: str, field) -> str:
        """Get the source field name for a FK (without _id suffix)."""
        source_field = getattr(field, 'source_field', field_name)
        if source_field and source_field.endswith('_id'):
            source_field = source_field[:-3]
        return source_field

    @classmethod
    def get_all_join_fields(cls):
        """Get all possible join fields for foreign key relationships.

        Returns:
            List of join field names in Django-style notation (e.g., 'guest__given_name')
        """
        join_fields = []
        for field_name, field in cls._meta.fields_map.items():
            if field.__class__.__name__ == 'ForeignKeyFieldInstance':
                related_model = getattr(field, 'related_model', None)
                if not related_model:
                    continue
                source_field = cls._get_fk_source_field(field_name, field)
                for related_field_name in related_model._meta.fields_db_projection.keys():
                    join_fields.append(f"{source_field}__{related_field_name}")
        return join_fields

    @classmethod
    def get_join_field_types(cls) -> dict[str, str]:
        """Get field types for all possible join fields.

        Returns:
            Dict mapping join field names to their types, e.g.:
            {'guest__given_name': 'CharField', 'guest__user_id': 'CharField'}
        """
        result = {}
        for field_name, field in cls._meta.fields_map.items():
            if field.__class__.__name__ == 'ForeignKeyFieldInstance':
                related_model = getattr(field, 'related_model', None)
                if not related_model:
                    continue
                source_field = cls._get_fk_source_field(field_name, field)
                for f in related_model.describe()["data_fields"]:
                    join_name = f"{source_field}__{f['name']}"
                    result[join_name] = f['field_type']
        return result

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

        return {return_as: getattr(self, field) for return_as, field in fields_for_select.items()}
