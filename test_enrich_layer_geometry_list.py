#!/usr/bin/env python
# coding: utf-8

import json
from pathlib import Path
from typing import List, Union

from arcgis.features import GeoAccessor
from arcgis.geometry import Geometry
import arcpy
import pandas as pd

# variables for testing
vars_lst = ['KeyUSFacts.TOTPOP_CY', 'KeyUSFacts.GQPOP_CY', 'KeyUSFacts.DIVINDX_CY', 'KeyUSFacts.TOTHH_CY',
            'KeyUSFacts.AVGHHSZ_CY', 'KeyUSFacts.MEDHINC_CY', 'KeyUSFacts.AVGHINC_CY', 'KeyUSFacts.PCI_CY',
            'KeyUSFacts.TOTHU_CY', 'KeyUSFacts.OWNER_CY', 'KeyUSFacts.RENTER_CY', 'KeyUSFacts.VACANT_CY',
            'KeyUSFacts.MEDVAL_CY', 'KeyUSFacts.AVGVAL_CY', 'KeyUSFacts.POPGRW10CY', 'KeyUSFacts.HHGRW10CY',
            'KeyUSFacts.FAMGRW10CY', 'KeyUSFacts.DPOP_CY', 'KeyUSFacts.DPOPWRK_CY', 'KeyUSFacts.DPOPRES_CY']
vars_str = ';'.join(vars_lst)
vars_nm_lst = ['KeyUSFacts_TOTPOP_CY', 'KeyUSFacts_GQPOP_CY', 'KeyUSFacts_DIVINDX_CY', 'KeyUSFacts_TOTHH_CY',
               'KeyUSFacts_AVGHHSZ_CY', 'KeyUSFacts_MEDHINC_CY', 'KeyUSFacts_AVGHINC_CY', 'KeyUSFacts_PCI_CY',
               'KeyUSFacts_TOTHU_CY', 'KeyUSFacts_OWNER_CY', 'KeyUSFacts_RENTER_CY', 'KeyUSFacts_VACANT_CY',
               'KeyUSFacts_MEDVAL_CY', 'KeyUSFacts_AVGVAL_CY', 'KeyUSFacts_POPGRW10CY', 'KeyUSFacts_HHGRW10CY',
               'KeyUSFacts_FAMGRW10CY', 'KeyUSFacts_DPOP_CY', 'KeyUSFacts_DPOPWRK_CY', 'KeyUSFacts_DPOPRES_CY']
poly_csv_pth = Path('enrich_polygons.csv')

# make sure output can be overwritten repeatedly
arcpy.env.overwriteOutput = True


def get_arcpy_geometry_list_from_csv(return_geometry: str = 'polygon',
                                     csv_pth: Path = poly_csv_pth) -> List[arcpy.PointGeometry]:
    """
    Utility function loading data from a CSV file, converting the geometries to a list of arcpy.Geometry objects and
    returning this list.
    """

    # load the data from a CSV file
    if isinstance(csv_pth, str):
        csv_pth = Path(csv_pth)
    assert csv_pth.exists(), 'The source csv file path does not appear to be valid.'

    # convert the geometries to valid arcgis.geometry.Geometry objects
    geom_df = pd.read_csv(csv_pth, index_col=0)
    geom_df.SHAPE = geom_df.SHAPE.apply(lambda geom: Geometry(json.loads(geom)))
    geom_df.spatial.set_geometry('SHAPE')

    # if points are desired, convert to point geometries
    if return_geometry.lower() == 'point' or return_geometry == 'points':
        geom_df.SHAPE = geom_df.SHAPE.apply(lambda geom: geom.true_centroid)
        geom_df.spatial.set_geometry('SHAPE')

    assert geom_df.spatial.validate(), 'Loaded points are not being recognized as valid geometries.'

    # use the arcgis.geometry.Geometry.as_arcpy method to convert to arcpy.Geometry object list
    arcpy_geom_lst = list(geom_df.SHAPE.apply(lambda geom: geom.as_arcpy))
    all_valid = all([isinstance(g, arcpy.Geometry) for g in arcpy_geom_lst])
    assert all_valid, 'Not all of the geometries are valid arcpy.PointGeometry objects.'

    return arcpy_geom_lst


def validate_enrich_results(enrich_fc: Union[Path, str], row_count: int = 1):
    """Helper function to validate enrich results."""

    # make sure all the fields for enrichment are present
    fc_nm_lst = [f.name for f in arcpy.ListFields(enrich_fc)]
    assert all([nm in fc_nm_lst for nm in vars_nm_lst])

    # make sure records are returned
    assert int(arcpy.management.GetCount(enrich_fc)[0]) >= row_count


def enrich_layer_test(geometry_type: str = 'polygon', buffer_type: str = None, distance: Union[int, float] = None,
                      unit: str = None) -> str:
    """Enrich a list of geometry objects loaded from a CSV."""

    # get the geometry list
    geom_lst = get_arcpy_geometry_list_from_csv(geometry_type)

    # call enrich layer to test
    enrich_fc = arcpy.ba.EnrichLayer(geom_lst, out_feature_class='memory/enriched_features',
                                     variables=vars_str, buffer_type=buffer_type,
                                     distance=distance,
                                     unit=unit)[0]

    validate_enrich_results(enrich_fc, len(geom_lst))


def enrich_layer_memory_test(geometry_type: str = 'polygon', buffer_type: str = None,
                             distance: Union[int, float] = None, unit: str = None) -> str:
    """Enrich a list of geometry objecst loaded from a CSV by saving in memory first."""

    # get the geometry list
    geom_lst = get_arcpy_geometry_list_from_csv(geometry_type)

    # convert geometry list to in memory feature class
    tmp_fc = arcpy.management.CopyFeatures(geom_lst, 'memory/tmp_pts')[0]

    # invoke enrichment using proximity around points
    enrich_fc = arcpy.ba.EnrichLayer(tmp_fc, out_feature_class='memory/enriched_features',
                                     variables=vars_str, buffer_type=buffer_type,
                                     distance=distance,
                                     unit=unit)[0]

    # remove memory feature class
    arcpy.management.Delete(tmp_fc)

    validate_enrich_results(enrich_fc, len(geom_lst))


def test_enrich_polygons():
    enrich_layer_test('polygon')


def test_enrich_points():
    enrich_layer_test('point')


def test_enrich_points_drive_time():
    enrich_layer_test('point', 'Driving Time', 5, 'Minutes')


def test_enrich_points_drive_distance():
    enrich_layer_test('point', 'Driving Distance', 5, 'Miles')


def test_enrich_polygons_memory():
    enrich_layer_memory_test('polygon')


def test_enrich_points_memory():
    enrich_layer_memory_test('point')


def test_enrich_points_memory_drive_time():
    enrich_layer_memory_test('point', 'Driving Time', 5, 'Minutes')


def test_enrich_points_memory_drive_distance():
    enrich_layer_memory_test('point', 'Driving Distance', 5, 'Miles')
