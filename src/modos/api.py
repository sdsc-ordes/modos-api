from __future__ import annotations
from collections.abc import Iterator
from dataclasses import asdict
from datetime import date
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any
import yaml

from linkml_runtime.dumpers import json_dumper
import rdflib
from loguru import logger
import modos_schema.datamodel as model
import numcodecs
from pydantic import HttpUrl
from pysam import AlignedSegment, VariantRecord
import zarr

from modos.rdf import attrs_to_graph
from modos.storage import (
    add_metadata_group,
    list_zarr_items,
    LocalStorage,
    S3Storage,
)
from modos.helpers.schema import (
    dict_to_instance,
    ElementType,
    set_data_path,
    set_haspart_relationship,
    UserElementType,
    update_haspart_id,
    update_metadata_from_model,
    DataElement,
)
from modos.genomics.formats import read_pysam
from modos.genomics.htsget import HtsgetConnection
from modos.genomics.region import Region
from modos.io import extract_metadata, parse_attributes
from modos.remote import EndpointManager, is_s3_path


class MODO:
    """Multi-Omics Digital Object
    A digital archive containing several multi-omics data and records
    connected by zarr-backed metadata.

    Parameters
    ----------
    path
        Path to the archive directory.
    id
        MODO identifier.
        Defaults to the directory name.
    name
        Human-readable name.
    description
        Human readable description.
    creation_date
        When the MODO was created.
    last_update_date
        When the MODO was last updated.
    has_assay
        Existing assay identifiers to attach to MODO.
    source_uri
        URI of the source data.
    endpoint
        URL to the modos server.
    s3_kwargs
        Keyword arguments for the S3 storage.
    services
        Optional dictionary of service endpoints.

    Attributes
    ----------
    storage: Storage
        Storage backend for the archive.
    endpoint: EndpointManager
        Server endpoint manager.

    Examples
    --------
    >>> demo = MODO("data/ex")

    # List identifiers of samples in the archive
    >>> demo.list_samples()
    ['sample/sample1']

    # List files in the archive
    >>> files = [str(x) for x in demo.list_files()]
    >>> assert 'demo1.cram' in files
    >>> assert 'reference.fa' in files
    """

    def __init__(
        self,
        path: Path | str,
        id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        creation_date: date = date.today(),
        last_update_date: date = date.today(),
        has_assay: list[str] = [],
        source_uri: str | None = None,
        endpoint: HttpUrl | None = None,
        s3_kwargs: dict[str, Any] | None = None,
        services: dict[str, HttpUrl] | None = None,
    ):
        self.endpoint = EndpointManager(endpoint, services or {})
        if is_s3_path(str(path)):
            if not self.endpoint.s3:
                raise ValueError("S3 path requires an endpoint.")
            logger.info(
                f"Using remote endpoint {endpoint} for {path}.",
                file=sys.stderr,
            )
            self.storage = S3Storage(str(path), self.endpoint.s3, s3_kwargs)
        else:
            # log to stderr
            logger.info(f"Using local storage for {path}")
            self.storage = LocalStorage(Path(path))
        # Opening existing object

        if self.storage.empty():
            self.id = id or self.path.name
            fields = {
                "@type": "MODO",
                "id": self.id,
                "creation_date": str(creation_date),
                "last_update_date": str(last_update_date),
                "name": name,
                "description": description,
                "has_assay": has_assay,
                "source_uri": source_uri,
            }
            # instantiate and post-process
            sanitized_fields = asdict(
                update_haspart_id(dict_to_instance(fields))
            )
            sanitized_fields["@type"] = "MODO"

            for key, val in sanitized_fields.items():
                if val:
                    self.zarr.attrs[key] = val
            zarr.consolidate_metadata(self.zarr.store)

    @property
    def zarr(self) -> zarr.Group:
        # NOTE: re-open every time to pick up changes
        # sometimes new groups are not picked up in zarr v3
        return zarr.open(self.storage.zarr.store_path)

    @property
    def is_remote(self) -> bool:
        return self.endpoint.s3 is not None

    @property
    def path(self) -> Path:
        return self.storage.path

    @property
    def metadata(self) -> dict[str, Any]:
        root = zarr.open_consolidated(self.zarr.store)

        if isinstance(root, zarr.Array):
            raise ValueError("Root must be a group. Empty archive?")

        # Get flat dictionary with all attrs, easier to search
        group_attrs = dict()
        # Document object itself
        root_id = root.attrs["id"]
        group_attrs[root_id] = dict(root.attrs)
        for subgroup in root.groups():
            group_type = subgroup[0]
            for name, value in list_zarr_items(subgroup[1]):
                group_attrs[f"{group_type}/{name}"] = dict(value.attrs)
        return group_attrs

    def knowledge_graph(self, uri_prefix: str | None = None) -> rdflib.Graph:
        """Return an RDF graph of the metadata. All identifiers
        are converted to valid URIs if needed."""
        if uri_prefix is None:
            uri_prefix = f"file://{self.path.name}/"
        kg = attrs_to_graph(self.metadata, uri_prefix=uri_prefix)
        return kg

    def show_contents(self, element: str | None = None) -> str:
        """Produces a YAML document of the object's contents.

        Parameters
        ----------
        element:
            Element, or group of elements (e.g. data or data/element_id) to show.
            If not provided, shows the metadata of the entire MODO.

        """
        meta = self.metadata

        if element in meta:
            data = meta[element]
        elif element in {g[0] for g in self.zarr.groups()}:
            data = {k: meta[k] for k in meta if k.startswith(element)}
        else:
            data = meta
        # Pretty print metadata contents as yaml

        return yaml.dump(data, sort_keys=False)

    def list_files(self) -> list[Path]:
        """Lists files in the archive recursively (except for the zarr file)."""
        return [
            file
            for file in self.storage.list()
            if file.parts[0] != "data.zarr"
        ]

    def list_arrays(self, element: str | None = None) -> Any:
        """Views arrays in the archive recursively.

        Parameters
        ----------
        element:
            Element, or group of elements (e.g. data or data/element_id) to show.
            If not provided, shows the metadata of the entire MODO.
        """
        root = zarr.open_consolidated(self.zarr.store)
        return root[element].tree() if element else root.tree()

    def query(self, query: str):
        """Use SPARQL to query the metadata graph"""
        return self.knowledge_graph().query(query)

    def list_samples(self):
        """Lists samples in the archive."""
        res = self.query("SELECT ?s WHERE { ?s a modos:Sample }")
        samples = []
        for row in res:
            for val in row:
                samples.append(
                    str(val).removeprefix(f"file://{self.path.name}/")
                )
        return samples

    def update_date(self, date: date = date.today()):
        """update last_update_date attribute"""
        self.zarr.attrs.update(last_update_date=str(date))

    def remove_element(self, element_id: str):
        """Remove an element from the archive, along with any files
        directly attached to it and links from other elements to it.
        """
        try:
            attrs = self.zarr[element_id].attrs
        except KeyError as err:
            logger.warning(f"Element {element_id} not found in the archive.")
            logger.info(f"Available elements are {list(self.metadata.keys())}")
            raise err

        # Remove data file
        if "data_path" in attrs.keys():
            try:
                data_file = self.path / attrs["data_path"]
            except TypeError:
                raise TypeError(
                    f"data_path must be a valid path, found: {attrs['data_path']}"
                )
            self.storage.remove(data_file)

        # Remove element group
        del self.zarr[element_id]

        # Remove links from other elements
        for elem, attrs in self.metadata.items():
            for key, value in attrs.items():
                if value == element_id:
                    del self.zarr[elem].attrs[key]
                elif isinstance(value, list) and element_id in value:
                    self.zarr[elem].attrs[key] = value.remove(element_id)

        self.update_date()
        zarr.consolidate_metadata(self.zarr.store)

    def remove_object(self):
        """Remove the complete modo object"""
        for fi in self.storage.list():
            self.storage.remove(fi)
        # Locally remove the empty directory (does not affect remote).
        if not self.is_remote:
            shutil.rmtree(self.path)
        logger.info(f"Permanently deleted {self.path}.")

    def add_element(
        self,
        element: (
            model.DataEntity
            | model.Sample
            | model.Assay
            | model.ReferenceGenome
        ),
        source_file: Path | None = None,
        part_of: str | None = None,
    ):
        """Add an element to the archive.
        If a data file is provided, it will be added to the archive.
        If the element is part of another element, the parent metadata
        will be updated.

        Parameters
        ----------
        element
            Element to add to the archive.
        source_file
            File to associate with the element.
        part_of
            Id of the parent element. It must be scoped to the type.
            For example "sample/foo".
        """

        self._add_any_element(
            element, source_file, part_of, allowed_elements=UserElementType
        )

    def _add_any_element(
        self,
        element: (
            model.DataEntity
            | model.Sample
            | model.Assay
            | model.ReferenceSequence
            | model.ReferenceGenome
        ),
        source_file: Path | None = None,
        part_of: str | None = None,
        allowed_elements: type = ElementType,
    ):
        """Add an element of any type to the storage. This is meant to be called internally to add elements automatically."""
        # Check that ID does not exist in modo
        if element.id in [Path(id).name for id in self.metadata.keys()]:
            raise ValueError(
                f"Please specify a unique ID. Element with ID {element.id} already exist."
            )

        # Copy data file to storage
        if source_file:
            # NOTE: Keep this for compatibility until ReferenceGenomes are handeled by refget
            if isinstance(element, model.ReferenceGenome):
                source_path = Path(source_file)
                target_path = Path(element._get("data_path"))
                with open(source_path, "rb") as src:
                    self.storage.put(src, target_path)

            # Add file (+ index) and update data_checksum attribute
            if isinstance(element, model.DataEntity):
                new_data = DataElement(element, self.storage)
                new_data.add_file(Path(source_file), Path(element.data_path))

        # Infer type
        type_name = allowed_elements.from_object(element).value
        type_group = self.zarr[type_name]
        element_path = f"{type_name}/{element.id}"

        # Assays are always bound to the MODO itself.
        if type_name == "assay" or part_of is not None:
            set_haspart_relationship(
                element.__class__.__name__,
                element_path,
                self.zarr[part_of] if part_of else self.zarr,
            )

        # Update haspart relationship
        element = update_haspart_id(element)

        # Add element to metadata
        attrs = json.loads(json_dumper.dumps(element))
        add_metadata_group(type_group, attrs)
        self.update_date()
        zarr.consolidate_metadata(self.zarr.store)

    def update_element(
        self,
        element_id: str,
        new: model.DataEntity | model.Sample | model.Assay | model.MODO,
        source_file: Path | None = None,
        part_of: str | None = None,
        allowed_elements: type = UserElementType,
    ):
        """Update element metadata in place by adding new values from model object.

        Parameters
        -----------------
        element_id
            Full id path in the zarr store.
        new
            Element containing the enriched metadata.
        """
        try:
            group = self.zarr[element_id]
        except KeyError:
            group = self.zarr.create_group(element_id)
        attr_dict = group.attrs.asdict()
        element = dict_to_instance(attr_dict | {"id": element_id})

        if not isinstance(new, type(element)):
            raise ValueError(
                f"Class {element.class_name} of {element_id} does not match {new.class_name}."
            )

        if isinstance(element, model.DataEntity):
            data = DataElement(element, self.storage)
            data.update_file(Path(new.data_path), source_file)
            # NOTE: data_checksum was updated in data, but needs to be synced into new
            new.data_checksum = data.model.data_checksum

        type_name = allowed_elements.from_object(new).value
        element_path = f"{type_name}/{new.id}"

        if part_of is not None:
            set_haspart_relationship(
                new.__class__.__name__, element_path, self.zarr[part_of]
            )

        new = update_haspart_id(new)
        update_metadata_from_model(group, new)
        self.update_date()
        zarr.consolidate_metadata(self.zarr.store)

    def enrich_metadata(self):
        """Enrich MODO metadata in place using content from associated data files."""

        # TODO: match using id instead of names -> safer
        # NOTE: will require handling type prefix.
        inst_names = {
            inst["name"]: id
            for id, inst in self.metadata.items()
            if "name" in inst
        }
        for id, entity in self.metadata.items():
            if entity.get("@type") != "DataEntity":
                continue
            try:
                data_inst = dict_to_instance(entity | {"id": id})
                extracted = extract_metadata(data_inst, self.path)
            # skip entities whose format does not support enrich
            except NotImplementedError:
                continue

            new_elements = []
            for ele in extracted.elements:
                if ele.name in inst_names:
                    self.update_element(inst_names[ele.name], ele)
                elif ele not in new_elements:
                    new_elements.append(ele)
                    self._add_any_element(ele)
                else:
                    continue

            # Add arrays if the parent is not an array already.
            parent = self.zarr[id]
            if extracted.arrays is None or not isinstance(parent, zarr.Group):
                continue

            # Nest arrays directly in parent group
            for name, arr in extracted.arrays.items():
                parent.create_dataset(
                    name, data=arr, object_codec=numcodecs.VLenUTF8()
                )

    def stream_genomics(
        self,
        file_path: str,
        region: str | None = None,
        reference_filename: str | None = None,
    ) -> Iterator[AlignedSegment | VariantRecord]:
        """Slices both local and remote CRAM, VCF (.vcf.gz), and BCF
        files returning an iterator over records.

        Parameters
        ----------
        file_path
            Path to the genomics file within the MODO.
        region
            Genomic region in UCSC format (e.g. chr1:1000-200
        reference_filename
            Path to the reference genome file.

        Returns
        -------
        Iterator over pysam AlignedSegment or VariantRecord objects.
        """

        _region = Region.from_ucsc(region) if region else None
        # check requested genomics file exists in MODO
        if Path(file_path) not in self.list_files():
            raise ValueError(f"{file_path} not found in {self.path}.")

        if self.endpoint.s3 and self.endpoint.htsget:
            con = HtsgetConnection(
                self.endpoint.htsget,
                Path(*self.path.parts[1:]) / file_path,
                region=_region,
            )
            stream = con.to_pysam(reference_filename=reference_filename)
        else:
            stream = read_pysam(
                self.path / file_path,
                reference_filename=reference_filename,
                region=_region,
            )

        return stream

    @classmethod
    def from_file(
        cls,
        config_path: Path,
        object_path: str,
        endpoint: HttpUrl | None = None,
        s3_kwargs: dict[str, Any] | None = None,
        services: dict[str, HttpUrl] | None = None,
        no_remove: bool = False,
    ) -> MODO:
        """build a modo from a yaml or json file"""
        element_list = parse_attributes(Path(config_path))

        # checks
        modo_count = sum(
            [ele["element"].get("@type") == "MODO" for ele in element_list]
        )
        if modo_count > 1:
            raise ValueError(
                f"There can not be more than one modo. Found {modo_count}"
            )
        ids = [ele["element"].get("id") for ele in element_list]
        if len(ids) > len(set(ids)):
            dup = {x for x in ids if ids.count(x) > 1}
            raise ValueError(
                f"Please specify unique IDs. Element(s) with ID(s) {dup} already exist."
            )

        instance_list = []
        modo_dict = {}
        for element in element_list:
            metadata = element["element"]
            args = element.get("args", {})
            if metadata.get("@type") == "MODO":
                del metadata["@type"]
                modo_dict["meta"] = metadata
                modo_dict["args"] = args
            else:
                metadata = set_data_path(metadata, args.get("source_file"))
                inst = dict_to_instance(metadata)
                instance_list.append((inst, args))
        modo = cls(
            path=object_path,
            endpoint=endpoint,
            services=services,
            s3_kwargs=s3_kwargs,
            **modo_dict.get("meta", {}),
            **modo_dict.get("args", {}),
        )

        modo_ids = {Path(id).name: id for id in modo.metadata.keys()}
        for inst, args in instance_list:
            if inst.id in modo_ids.keys():
                modo.update_element(modo_ids[inst.id], inst, **args)
            else:
                modo.add_element(inst, **args)
        if no_remove:
            return modo
        modo_id = modo.zarr.attrs["id"]
        old_ids = [
            id for id in modo_ids.keys() if id not in ids and id != modo_id
        ]
        for old_id in old_ids:
            modo.remove_element(modo_ids[old_id])
        return modo

    def download(self, target_path: Path):
        """Download the MODO to a local directory.
        This will download all files and metadata to the target directory.
        """
        self.storage.transfer(LocalStorage(target_path))

    def upload(
        self,
        target_path: Path,
        s3_endpoint: HttpUrl,
        s3_kwargs: dict[str, Any] | None = None,
    ):
        """Upload a local MODO to a target_path on a remote endpoint."""
        self.storage.transfer(S3Storage(target_path, s3_endpoint, s3_kwargs))

    def encrypt(
        self,
        recipient_pubkeys: list[os.PathLike] | os.PathLike,
        seckey_path: os.PathLike | None = None,
        passphrase: str | None = None,
        delete: bool = True,
    ):
        """Encrypt genomic data files including index files in a modo using crypt4gh"""
        for id, group in self.zarr["data"].members():
            meta = group.attrs.asdict()
            meta["id"] = id
            data = DataElement(dict_to_instance(meta), self.storage)
            data.encrypt(
                recipient_pubkeys,
                seckey_path,
                passphrase,
                delete,
            )
            update_metadata_from_model(group, data.model)
        self.update_date()

    def decrypt(
        self,
        seckey_path: os.PathLike,
        sender_pubkey: os.PathLike | None = None,
        passphrase: str | None = None,
    ):
        """Decrypt all c4gh encrypted data files in modo"""
        for id, group in self.zarr["data"].members():
            meta = group.attrs.asdict()
            meta["id"] = id
            data = DataElement(dict_to_instance(meta), self.storage)
            data.decrypt(seckey_path, sender_pubkey, passphrase)
            update_metadata_from_model(group, data.model)
        self.update_date()
