from tortoise import fields

from .rdm_model import RdmModel


class MultitenantRdmModel(RdmModel):
    """Abstract RdmModel subclass that declares the `tenant` scoping field.

    Concrete models intended for use with `MultitenantTortoiseStore` should
    subclass this instead of `RdmModel`, so the tenant column is declared
    once and indexed consistently.

    Concrete subclasses MUST write their inner Meta as
    `class Meta(RdmModel.Meta): table = "..."` (inheriting from RdmModel.Meta,
    NOT MultitenantRdmModel.Meta), otherwise `abstract = True` leaks via MRO
    and Tortoise will not generate a table for the subclass.
    """

    tenant = fields.CharField(max_length=64, index=True)

    class Meta(RdmModel.Meta):
        abstract = True
