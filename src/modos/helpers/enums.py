from enum import Enum


class UserElementType(str, Enum):
    """Enumeration of element types exposed to the user."""

    SAMPLE = "sample"
    ASSAY = "assay"
    DATA_ENTITY = "data"
    REFERENCE_GENOME = "reference"

    def get_target_class(
        self,
    ) -> type:
        """Return the target class for the element type."""
        import modos_schema.datamodel as model

        match self:
            case UserElementType.SAMPLE:
                return model.Sample
            case UserElementType.ASSAY:
                return model.Assay
            case UserElementType.DATA_ENTITY:
                return model.DataEntity
            case UserElementType.REFERENCE_GENOME:
                return model.ReferenceGenome
            case _:
                raise ValueError(f"Unknown element type: {self}")

    @classmethod
    def from_object(cls, obj):
        """Return the element type from an object."""
        import modos_schema.datamodel as model

        match obj:
            case model.Sample():
                return UserElementType.SAMPLE
            case model.Assay():
                return UserElementType.ASSAY
            case model.DataEntity():
                return UserElementType.DATA_ENTITY
            case model.ReferenceGenome():
                return UserElementType.REFERENCE_GENOME
            case _:
                raise ValueError(f"Unknown object type: {type(obj)}")


class ElementType(str, Enum):
    """Enumeration of all element types."""

    SAMPLE = "sample"
    ASSAY = "assay"
    DATA_ENTITY = "data"
    REFERENCE_GENOME = "reference"
    REFERENCE_SEQUENCE = "sequence"

    def get_target_class(
        self,
    ) -> type:
        """Return the target class for the element type."""
        import modos_schema.datamodel as model

        match self:
            case ElementType.SAMPLE:
                return model.Sample
            case ElementType.ASSAY:
                return model.Assay
            case ElementType.DATA_ENTITY:
                return model.DataEntity
            case ElementType.REFERENCE_GENOME:
                return model.ReferenceGenome
            case ElementType.REFERENCE_SEQUENCE:
                return model.ReferenceSequence
            case _:
                raise ValueError(f"Unknown element type: {self}")

    @classmethod
    def from_object(cls, obj):
        """Return the element type from an object."""
        import modos_schema.datamodel as model

        match obj:
            case model.Sample():
                return ElementType.SAMPLE
            case model.Assay():
                return ElementType.ASSAY
            case model.DataEntity():
                return ElementType.DATA_ENTITY
            case model.ReferenceGenome():
                return ElementType.REFERENCE_GENOME
            case model.ReferenceSequence():
                return ElementType.REFERENCE_SEQUENCE
            case _:
                raise ValueError(f"Unknown object type: {type(obj)}")

    @classmethod
    def from_model_name(cls, name: str):
        """Return the element type from an object name."""

        match name:
            case "Sample":
                return ElementType.SAMPLE
            case "Assay":
                return ElementType.ASSAY
            case "DataEntity":
                return ElementType.DATA_ENTITY
            case "ReferenceGenome":
                return ElementType.REFERENCE_GENOME
            case "ReferenceSequence":
                return ElementType.REFERENCE_SEQUENCE
            case _:
                raise ValueError(f"Unknown object type: {name}")
