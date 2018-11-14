import bson
import gzip

from pulp.server.webservices.views import serializers as platform_serializers


class Distribution(platform_serializers.ModelSerializer):
    """
    Serializer for Distribution based models
    """
    class Meta:
        remapped_fields = {'distribution_id': 'id'}


class Drpm(platform_serializers.ModelSerializer):
    """
    Serializer for Drpm based models
    """
    class Meta:
        remapped_fields = {}


class RpmBase(platform_serializers.ModelSerializer):
    """
    Serializer for RpmBase based models
    """
    class Meta:
        remapped_fields = {}
        rewrite_fields = {('size', ): 'file_size', ('signing_key', ): 'signature'}

    def serialize(self, unit):
        """
        Convert a single unit to it's dictionary form.

        Decompress values of the `repodata` dict field for RPM/SRPM units.

        :param unit: The object to be converted
        :type unit: object
        """
        for metadata_type in unit.get('repodata', {}):
            metadata = unit['repodata'][metadata_type]
            unit['repodata'][metadata_type] = gzip.zlib.decompress(metadata)
        signature = unit.get('signing_key')
        if signature:
            unit['signature'] = signature
        file_size = unit.get('size')
        if file_size:
            unit['file_size'] = file_size
        return super(RpmBase, self).serialize(unit)


class Errata(platform_serializers.ModelSerializer):
    """
    Serializer for Errata models
    """
    class Meta:
        remapped_fields = {'errata_from': 'from',
                           'errata_id': 'id'}

    def serialize(self, unit):
        """
        Convert a single unit to it's dictionary form.

        Add to errratum unit its pkglist if needed.
        Duplicated pkglists are eliminated.

        :param unit: The object to be converted
        :type unit: object
        """
        from pulp_rpm.plugins.db import models

        # If pkglist field is absent, it's on purpose, e.g. not specified in the fields during
        # search. So it should not be added during serialization.
        # If pkglist field is present, it's always emtpy => it should be filled in.
        if 'pkglist' in unit:
            errata_id = unit.get('errata_id')
            # If fields in search criteria don't include errata_id
            if errata_id is None:
                erratum_obj = models.Errata.objects.only('errata_id').get(id=unit.get('_id'))
                errata_id = erratum_obj.errata_id

            match_stage = {'$match': {'errata_id': errata_id}}
            unwind_stage = {'$unwind': '$collections'}
            group_stage = {'$group': {'_id': '$collections.module',
                                      'packages': {'$addToSet': '$collections.packages'}}}
            collections = models.ErratumPkglist.objects.aggregate(
                match_stage, unwind_stage, group_stage, allowDiskUse=True)
            for collection_idx, collection in enumerate(collections):
                # To preserve the original format of a pkglist the 'short' and 'name'
                # keys are added. 'short' can be an empty string, collection 'name'
                # should be unique within an erratum.
                item = {'packages': collection['packages'][0],
                        'short': '',
                        'name': 'collection-%s' % collection_idx}
                if collection['_id']:
                        item['module'] = collection['_id']
                unit['pkglist'].append(item)

        return super(Errata, self).serialize(unit)


class PackageGroup(platform_serializers.ModelSerializer):
    """
    Serializer for a PackageGroup models
    """
    class Meta:
        remapped_fields = {'package_group_id': 'id'}


class PackageCategory(platform_serializers.ModelSerializer):
    """
    Serializer for a PackageCategory models
    """
    class Meta:
        remapped_fields = {'package_category_id': 'id'}


class PackageEnvironment(platform_serializers.ModelSerializer):
    """
    Serializer for a PackageEnvironment models
    """
    class Meta:
        remapped_fields = {'package_environment_id': 'id'}


class PackageLangpacks(platform_serializers.ModelSerializer):
    """
    Serializer for a PackageLangpacks models
    """
    class Meta:
        remapped_fields = {}


class YumMetadataFile(platform_serializers.ModelSerializer):
    """
    Serializer for a YumMetadataFile models
    """
    class Meta:
        remapped_fields = {}


class ISO(platform_serializers.ModelSerializer):
    """
    Serializer for a ISO models
    """
    class Meta:
        remapped_fields = {}
        #rewrite_fields = {'pulp_user_metadata.abstract': 'abstract', 'pulp_user_metadata.install_media': 'install_media'}
        rewrite_fields = {('pulp_user_metadata', 'abstract'): 'abstract',
                          ('pulp_user_metadata', 'install_media'): 'install_media'}

    def serialize(self, unit):
        """
        Convert a single unit to it's dictionary form.

        :param unit: The object to be converted
        :type unit: object
        """
        pulp_user_metadata = unit.get('pulp_user_metadata')
        if pulp_user_metadata:
            abstract = pulp_user_metadata.get('abstract')
            install_media = pulp_user_metadata.get('install_media')
            if abstract is not None:
                unit['abstract'] = abstract
            if install_media is not None:
                unit['install_media'] = install_media
        return super(ISO, self).serialize(unit)


class Modulemd(platform_serializers.ModelSerializer):
    """
    Serializer for a Modulemd models
    """
    class Meta:
        remapped_fields = {}


class ModulemdDefaults(platform_serializers.ModelSerializer):
    """
    Serializer for ModulemdDefaults models
    """
    class Meta:
        remapped_fields = {}

    def serialize(self, unit):
        """
        Decode profiles field from BSON to JSON.

        :param unit: The object to be converted
        :type unit: object
        """
        profiles = bson.BSON(unit.get('profiles'))
        unit['profiles'] = profiles.decode()

        return super(ModulemdDefaults, self).serialize(unit)
