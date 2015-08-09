#!/usr/bin/env python2
""" Generate demo test-results data.

    This program is used to create fake results from daily runs against a
    hypothetical user database called "Westwind".  This hypothetical
    database has the following tables within it:
       - cust_type - a small, non-partitioned lookup table with 5 rows
       - asset_type - a small, non-partitioned lookup table with 5 rows
       - cust_asset_events - a large, partitioned fact table

    There are three tests for the two lookup tables, and six for the large
    fact table that run daily.  The program generates one run for every day
    from 2015-01-01 to 2015-12-31.  A small random number of tests will find
    violations.  The user tables that this demo creates tests for include:
        - cust_type                (~ 5 rows)
        - asset_type               (~ 5 rows)
        - event_type               (~ 5 rows)
        - dates                    (~ 3650 rows)
        - locations                (tbd)
        - customers                (~ 10,000 rows)
        - assets                   (~ 10,000,000 rows)
        - cust_asset_events        (~ 3,000,000,000 rows) = avg of 1 event/asset/day for 7 years
        - cust_asset_event_month   (~ 840,000,000 rows) = 1 row/asset/month for 7 years

    This results data will be written by default to /tmp/inspector_demo.csv.
    4380 records will be written to this comma-delimited csv file without
    any quotes.  The fields are in the following order:
        - instance_name             STRING    (always 'prod')
        - database_name             STRING    (always 'westwind')
        - table_name                STRING
        - table_partitioned         INTEGER   (1=True, 0=False)
        - run_start_timestamp       TIMESTAMP (YYYY-MM-DD HH:MM:SS)
        - run_mode                  STRING    ('full' or 'incremental')
        - partition_key             STRING    ('' or 'date_id')
        - partition_value           STRING    (5-digit julian date for partitioned tables)
        - check_name                STRING
        - check_policy_type         STRING    ('quality' or 'data-management')
        - check_type                STRING    ('rule')
        - run_check_start_timestamp TIMESTAMP (YYYY-MM-DD HH:MM:SS)
        - run_check_end_timestamp   TIMESTAMP (YYYY-MM-DD HH:MM:SS)
        - run_check_mode            STRING    ('full' or 'incremental')
        - run_check_rc              INTEGER   (always 0)
        - run_check_violation_cnt   INTEGER
        - run_check_anomaly_score   INTEGER   (always 0)
        - run_check_scope           INTEGER   (0-100)
        - run_check_unit            STRING    ('tables' or 'rows')
        - run_check_severity_score  INTEGER   (0-100)
        - run_check_validated       STRING    (always '')


"""
from __future__ import division
import os, sys
import random
import argparse
import time, datetime
from os.path import join as pjoin
from os.path import isfile, isdir, exists
import csv
import random

__version__ = '0.0.1'
user_tables = \
    {'cust_type':
        {'cols':
            {'cust_type_id',
             'cust_type_name',
            },
         'mode': 'full',
         'partition_key': None,
         'partition_row_cnt_avg': 5,
         'checks':
            {'cust_type_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'cust_name_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'cust_not_empty':
                {'policy_type':     'quality',
                 'violation_unit':  'tables',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'stats_exist':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
             'stats_not_stale':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
            }
        }
    ,
    'asset_type':
        {'cols':
            {'asset_type_id',
             'asset_type_name',
            },
         'mode': 'full',
         'partition_key': None,
         'partition_row_cnt_avg': 5,
         'checks':
            {'asset_type_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'asset_name_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'asset_not_empty':
                {'policy_type':     'quality',
                 'violation_unit':  'tables',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'stats_exist':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
             'stats_not_stale':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
            }
        }
    ,
    'event_type':
        {'cols':
            {'event_type_id',
             'event_type_name',
            },
         'mode': 'full',
         'partition_key': None,
         'partition_row_cnt_avg': 5,
         'checks':
            {'event_type_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'event_name_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'event_not_empty':
                {'policy_type':     'quality',
                 'violation_unit':  'tables',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'stats_exist':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
             'stats_not_stale':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
            }
        }
    ,
    'customers':
        {'cols':
            {'cust_id',
             'cust_name',
             'cust_status',
             'cust_type_id'
            },
         'mode': 'full',
         'partition_key': None,
         'partition_row_cnt_avg': 10000,
         'checks':
            {'cust_id_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'check_type':      'rule' },
             'cust_name_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'check_type':      'rule' },
             'cust_status_ck':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'check_type':      'rule' },
             'cust_typeid_fk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'check_type':      'rule' },
             'stats_exist':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
             'stats_not_stale':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.1,
                 'check_type':      'rule' },
            }
        }
    ,
    'assets':
        {'cols':
            {'cust_id',
             'asset_id',
             'asset_name',
             'asset_status',
             'asset_type_id'
            },
         'mode': 'full',
         'partition_key': None,
         'partition_row_cnt_avg': 10000000,
         'checks':
            {'asset_id_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'check_type':      'rule' },
             'asset_name_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'check_type':      'rule' },
             'asset_status_ck':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'check_type':      'rule' },
             'asset_typeid_fk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'check_type':      'rule' },
             'stats_exist':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
             'stats_not_stale':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.1,
                 'check_type':      'rule' },
            }
        }
    ,
    'dates':
        {'cols':
            {'date_id',
             'date_name',
             'year',
             'quarter_of_year',
             'month_of_year',
             'month_name',
             'week_of_year_iso',
             'day_of_month',
             'day_of_year',
             'day_of_week',
             'day_name',
             'day_name_abbrev'
            },
         'mode': 'full',
         'partition_key': None,
         'partition_row_cnt_avg': 3650,
         'checks':
            {'date_id_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'date_name_uk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'monthofyear_range_ck':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'weekofyear_range_ck':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'dayofmonth_range_ck':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'dates_not_empty':
                {'policy_type':     'quality',
                 'violation_unit':  'tables',
                 'severity':        'high',
                 'mode':            'full',
                 'failure_rate':    0.01,
                 'check_type':      'rule' },
             'stats_exist':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
             'stats_not_stale':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
            }
        }
    ,
    'cust_asset_events':
        {'cols':
            {'cust_id',
             'asset_id',
             'event_id',
             'date_id',
             'event_type_id',
            },
         'mode': 'incremental',
         'partition_key': 'date_id',
         'partition_row_cnt_avg': 400000000, # 400 mil
         'checks':
            {'cust_id_fk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'asset_id_fk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'date_id_fk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'event_type_id_fk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'event_id_not_null':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'table_not_empty':
                {'policy_type':     'quality',
                 'violation_unit':  'tables',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'stats_exist':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
             'stats_not_stale':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.1,
                 'check_type':      'rule' },
            },
        },
    'cust_asset_event_months':
        {'cols':
            {'cust_id',
             'asset_id',
             'month_id',
             'event_type_id',
             'event_count',
            },
         'mode': 'incremental',
         'partition_key': 'date_id',
         'partition_row_cnt_avg': 40000000, # 40 mil
         'checks':
            {'cust_id_fk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'asset_id_fk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'month_id_fk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'event_type_id_fk':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'event_count_consistency_ck':
                {'policy_type':     'consistency',
                 'violation_unit':  'rows',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'cols_not_null':
                {'policy_type':     'quality',
                 'violation_unit':  'rows',
                 'severity':        'medium',
                 'mode':            'incremental',
                 'failure_rate':    0.1,
                 'check_type':      'rule' },
             'table_not_empty':
                {'policy_type':     'quality',
                 'violation_unit':  'tables',
                 'severity':        'high',
                 'mode':            'incremental',
                 'check_type':      'rule' },
             'stats_exist':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.001,
                 'check_type':      'rule' },
             'stats_not_stale':
                {'policy_type':     'data-management',
                 'violation_unit':  'tables',
                 'severity':        'low',
                 'mode':            'full',
                 'failure_rate':    0.1,
                 'check_type':      'rule' },
            }
        }
    }



def main():
    args = get_args()
    create_test_file(dirname=args.target_dir)
    print('Demo file created in dir: %s' % args.target_dir)



def create_test_file(dirname):
    assert isdir(dirname)
    fieldnames = ('instance_name', 'database_name', 'table_name',
                  'table_partitioned', 'run_start_timestamp', 'run_mode',
                  'partition_key', 'partition_value', 'check_name',
                  'check_policy_type', 'check_type',
                  'run_check_start_timestamp', 'run_check_end_timestamp',
                  'run_check_mode', 'run_check_rc', 'run_check_violation_cnt',
                  'run_check_anomaly_score', 'run_check_scope', 'run_check_unit',
                  'run_check_severity_score', 'run_check_validated')

    outfile = open(pjoin(dirname, 'inspector_demo.csv'), 'w')
    outfile.write(','.join(fieldnames) + '\n')
    writer  = csv.DictWriter(outfile, fieldnames)
    # Establish instance name
    # Establish database name
    #for day_of_year in range(1,365):
    curr_datetime = None
    for month_of_year in range(1,13):
        for day_of_month in range(1, get_month_days(month_of_year)+1):
            #print('2015-%-2.2d-%-2.2d' % (month_of_year, day_of_month))
            run_start_datetime   = get_run_start_datetime(2015, month_of_year, day_of_month)
            for table_name in user_tables:
                #print('    table_name: %s' % table_name)
                for check_name in user_tables[table_name]['checks']:
                    #print('        check_name: %s' % check_name)
                    curr_datetime                         = get_curr_datetime(curr_datetime, run_start_datetime)
                    row_dict = {}
                    row_dict['instance_name']             = get_instance_name()
                    row_dict['database_name']             = get_database_name()
                    row_dict['table_name']                = table_name
                    row_dict['table_partitioned']         = get_table_partitioned(user_tables[table_name]['partition_key'])
                    row_dict['run_start_timestamp']       = get_ts_from_dt(run_start_datetime)
                    row_dict['run_mode']                  = user_tables[table_name]['mode']
                    row_dict['partition_key']             = get_partition_key(user_tables[table_name]['partition_key'])
                    row_dict['partition_value']           = get_partition_value(row_dict['run_mode'], curr_datetime)
                    row_dict['check_name']                = check_name
                    row_dict['check_policy_type']         = get_check_policy_type(user_tables[table_name]['checks'][check_name]['policy_type'])
                    row_dict['check_type']                = get_check_type(user_tables[table_name]['checks'][check_name]['check_type'])
                    row_dict['run_check_start_timestamp'] = get_ts_from_dt(curr_datetime)
                    row_dict['run_check_end_timestamp']   = get_ts_from_dt(curr_datetime + datetime.timedelta(seconds=1))
                    row_dict['run_check_mode']            = get_run_check_mode(user_tables[table_name]['mode'],
                                                                               user_tables[table_name]['checks'][check_name]['mode'])
                    row_dict['run_check_rc']              = '0'
                    row_dict['run_check_violation_cnt']   = get_violation_cnt(table_name, check_name)

                    row_dict['run_check_unit']            = user_tables[table_name]['checks'][check_name]['violation_unit']
                    row_dict['run_check_scope']           = get_scope(user_tables[table_name]['partition_key'],
                                                                      user_tables[table_name]['partition_row_cnt_avg'],
                                                                      user_tables[table_name]['checks'][check_name]['violation_unit'],
                                                                      row_dict['run_check_violation_cnt'])

                    default_severity_name  = user_tables[table_name]['checks'][check_name]['severity']
                    default_severity_score = convert_severity(default_severity_name)

                    row_dict['run_check_severity_score']  = get_severity_score(default_severity_score,
                                                                               row_dict['run_check_scope'])
                    row_dict['run_check_anomaly_score']   = '0'
                    row_dict['run_check_validated']       = ''
                    writer.writerow(row_dict)
    outfile.close()


def get_violation_cnt(table_name, check_name):
    mode           = user_tables[table_name]['mode']
    partition_key  = user_tables[table_name]['partition_key']
    avg_row_cnt    = user_tables[table_name]['partition_row_cnt_avg']
    violation_unit = user_tables[table_name]['checks'][check_name]['violation_unit']
    failure_rate   = user_tables[table_name]['checks'][check_name].get('failure_rate', 0.1)

    if random.random() < failure_rate:
        if violation_unit == 'table':
            return 1
        else:
            if partition_key is None and random.random() < 0.5:
                # screwed up the all rows, probably because you reloaded 100% of
                # the data wrong.  Maybe due to:
                #    - loaded same data twice
                #    - failed to load
                return int(avg_row_cnt)
            else:
                # screwed up a subset of rows, probably a subset of a single
                # partition
                return int(avg_row_cnt * random.random())
    else:
        return 0


def get_partition_value(run_mode, curr_datetime):
    if run_mode is None:
        return None
    else:
        tt = curr_datetime.timetuple()
        return '%d%03d' % (tt.tm_year, tt.tm_yday)


def get_run_check_mode(run_mode, check_mode):
    if run_mode == 'incremental' and check_mode == 'incremental':
        return 'incremental'
    else:
        return 'full'


def convert_severity(in_val):
    if in_val is None:
        return 0
    elif in_val == 'low':
        return 10
    elif in_val == 'medium':
        return 50
    elif in_val == 'high':
        return 100
    else:
        print('error: invalid convert_severity in_val: %s' % in_val)
        sys.exit(1)


def get_scope(partition_key, avg_row_cnt, violation_unit, violation_cnt):
    """ Returns the scope of the violations.
        Range is 0 to 100 - 100 being the greatest scope
    """
    if not violation_cnt:
        return 0
    elif violation_unit == 'tables':
        return 100
    else:
        if partition_key is None:
            return (violation_cnt / avg_row_cnt) * 100
        else:
            # assumes 100 partitions, or maybe more but recent
            # data is more valuable
            return (violation_cnt / avg_row_cnt)


def get_severity_score(default_severity_score, scope):
    """ Returns the severity of the violations.
        Range is 0 to 100 - 100 being the most severe.
    """
    severity_score = (scope * default_severity_score) / 100
    if severity_score == 0:
        return 0
    else:
        return int(max(1, min(100, severity_score)))


def get_partition_key(raw_partition_key):
    if raw_partition_key is None:
        return ''
    else:
        return raw_partition_key


def get_instance_name():
    return 'prod'


def get_database_name():
    return 'westwind'


def get_table_partitioned(partition_key):
    if partition_key is not None and partition_key != '':
        return '1'
    else:
        return '0'

def get_run_start_datetime(year, month, day):
    hour    = 2
    minute  = 0
    second  = 0
    d = datetime.datetime(2015, month, day, hour, minute, second)
    return d

def get_ts_from_dt(dt):
    ts_format  = '%Y-%m-%d %H:%M:%S'
    return dt.strftime(ts_format)

def get_curr_datetime(curr_datetime, run_start_datetime):
    if curr_datetime is None:
        # first time used
        return run_start_datetime
    elif curr_datetime > run_start_datetime:
        # after the first tie for a day
        return curr_datetime + datetime.timedelta(seconds=1)
    else:
        # first time for a day
        return run_start_datetime


def get_month_days(month_of_year):
    if month_of_year in (1,3,5,7,8,10,12):
        return 31
    elif month_of_year in (2,):
        return 28
    else:
        return 30


def get_check_policy_type(raw_check_policy_type):
    return raw_check_policy_type


def get_check_type(raw_check_type):
    return raw_check_type




def get_args():
    parser = argparse.ArgumentParser(description='Generates demo data')
    parser.add_argument('--version',
                        action='version',
                        version=__version__,
                        help='displays version number')
    parser.add_argument('--long-help',
                        action='store_true',
                        help='Provides more verbose help')
    parser.add_argument('--target-dir',
                        default='/tmp',
                        help='Specifies the directory the demo data will be written to.  Default is \\tmp')

    args = parser.parse_args()
    if args.long_help:
        print(__doc__)
        sys.exit(0)

    if not isdir(args.target_dir):
        print('Invalid target_dir: %s' % args.target_dir)
        raise ValueError, 'Invalid target_dir'

    return args


if __name__ == '__main__':
   sys.exit(main())

