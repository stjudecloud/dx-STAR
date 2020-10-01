#!/usr/bin/env python

"""
Title: STAR Alignment for RNA sequences
Author(s): Clay McLeod
Date: July 6, 2016
Description: Performs the STAR alignment process on RNA data, usually in
             preparation for use by cicero.

                         +
                         |
                         |
            +------------v-------------+
            |                          |
            |      Data Download       |
            |       (Parallel)         |
            |                          |
            +------------+-------------+
                         |
                         |
            +------------v-------------+
            |                          |
            |       Unarchiving        |
            |       (Parallel)         |
            |                          |
            +------------+-------------+
                         |
                         |
            +------------v-------------+
            |                          |
            |      STAR Alignment      |
            |        (Parallel)        |
            |                          |
            +------------+-------------+
                         |
                         |
            +------------v-------------+
            |                          |
            |       SAM -> BAM         |
            |       (Parallel)         |
            |                          |
            +------------+-------------+
                         |
                         |
            +------------v-------------+
            |                          |
            |        Index BAM         |
            |        (Parallel)        |
            |                          |
            +------------+-------------+
                         |
                         |
            +------------v-------------+
            |                          |
            |    Sort BAM Coordinate   |
            |        (Parallel)        |
            |                          |
            +------------+-------------+
                         |
                         |
                         v
"""

from __future__ import print_function

import os
import os.path
import sys
import dxpy
import time
import glob
import subprocess

verbose = True


class Timer:
    """Utility to wrap timing of functions"""

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.interval = self.end - self.start


def printv(outstr, end="\n"):
    """Only prints if the class variable 'verbose' is True. this
    is a useful helper for quickly turning on and off output while
    ensuring that output is flushed immediately to stdout in
    Python 2."""

    if verbose:
        sys.stdout.write(outstr + end)
        sys.stdout.flush()


def Popen(cmd):
    """Helper method for opening a process"""
    return subprocess.Popen(cmd, shell=True)


def get_vars_metadata():
    """DNAnexus automatically injects some useful, undocumented variables
    into bash scripts, such as "$<varname>_prefix", and "$<varname>_path".
    This method wraps the functionality that injects those bash vars so
    they can be used in Python"""

    from dxpy.utils.file_load_utils import gen_bash_vars
    return gen_bash_vars("job_input.json")

VARS = None


def get_dx_var(var_name):
    """Utility method for looking up useful bash vars (see get_vars_metadata)
    and presenting them in a way that is cogent for Python"""

    global VARS

    if not VARS:
        VARS = get_vars_metadata()

    if var_name[0] == '$':
        var_name = var_name[1:]

    return VARS[var_name].replace('(', '').replace(')', '').strip()

def download_ref_files(GENOME):
    """Utility to download/unzip/untar reference files concurrently"""
    
    # Download STAR reference files
    p1 = Popen("dx download -r project-F5444K89PZxXjBqVJ3Pp79B4:/global/reference/Homo_sapiens/%s/STAR" % (GENOME))
    
    p1.wait()

def download_all_files(FASTQ_R1, FASTQ_R1_PREFIX, FASTQ_R2, FASTQ_R2_PREFIX, GENOME):
                       #STAR_INDEX_ARCHIVE, TRANSCRIPTOME_GTF):
    """Utility to download/unzip/untar all files concurrently"""

    # Download/unzip/untar all files in parallel, piping for speed increase
    p1 = Popen("dx cat %s | pigz -d - > %s.fastq" %
               (FASTQ_R1, FASTQ_R1_PREFIX))
    p2 = Popen("dx cat %s | pigz -d - > %s.fastq" %
               (FASTQ_R2, FASTQ_R2_PREFIX))
    #p3 = Popen("tar -xf /home/dnanexus/GRCh37-lite.STAR.index.tar.gz " \
    #           "--owner root --group root --no-same-owner")
    p3 = Popen("dx download -r project-F5444K89PZxXjBqVJ3Pp79B4:/global/reference/Homo_sapiens/%s/STAR" % (GENOME))

    # Wait for all files to be processed
    p1.wait()
    p2.wait()
    p3.wait()


@dxpy.entry_point('main')
def main(fastq_r1, fastq_r2, ref_name):
    """Only entry point for this applet"""

    #########
    # Setup #
    #########

    # From bash injections
    FASTQ_R1 = get_dx_var("$fastq_r1")
    FASTQ_R2 = get_dx_var("$fastq_r2")
    FASTQ_R1_PREFIX = get_dx_var("$fastq_r1_prefix")
    FASTQ_R2_PREFIX = get_dx_var("$fastq_r2_prefix")
    GENOME = get_dx_var("$ref_name")

    # Calculated
    FASTQ_R1_ABS_FILEPATH = FASTQ_R1_PREFIX + ".fastq"
    FASTQ_R2_ABS_FILEPATH = FASTQ_R2_PREFIX + ".fastq"
    TRANSCRIPTOME_GTF_ABS_FILEPATH = "/home/dnanexus/STAR/refFlat_no_junk.gtf"

    printv("=== Setup ===")
    printv("  [*] Fastq R1: %s" % (FASTQ_R1_ABS_FILEPATH))
    printv("  [*] Fastq R2: %s" % (FASTQ_R2_ABS_FILEPATH))
    printv("  [*] Transcriptome GTF: %s" % (TRANSCRIPTOME_GTF_ABS_FILEPATH))
    printv("")

    ###############
    # Downloading #
    ###############

    printv("=== Downloading/Unzipping files ===")
    printv("  [*] Downloading files...", end="")

    # Download all data
    with Timer() as t:
        download_all_files(FASTQ_R1, FASTQ_R1_PREFIX, FASTQ_R2, FASTQ_R2_PREFIX, GENOME)

    printv("took %d seconds." % (t.interval))

    ##################
    # STAR Alignment #
    ##################

    printv("")
    printv("=== STAR Alignment ===")
    printv("  [*] Performing alignment...", end="")

    # Perform STAR alignment
    with Timer() as t:
        os.system("sudo chmod +x /STAR; /STAR --runMode alignReads --genomeDir STAR --readFilesIn %s %s "
                  "--runThreadN `nproc` --sjdbGTFfile %s --outSAMstrandField "
                  "intronMotif --chimSegmentMin 10 --chimJunctionOverhangMin 10 "
                  "--outSAMtype BAM SortedByCoordinate --outBAMsortingThreadN `nproc` "
                  "--outBAMcompression 5 --limitBAMsortRAM 80000000000"
                  "> /dev/null" % (FASTQ_R1_ABS_FILEPATH,
                                   FASTQ_R2_ABS_FILEPATH,
                                   TRANSCRIPTOME_GTF_ABS_FILEPATH))
    printv("took %d seconds." % (t.interval))

    #################
    # Move BAM file #
    #################

    # Start with FASTQ basename
    new_bam_name = os.path.basename(FASTQ_R1_ABS_FILEPATH)

    # Remove file extension
    new_bam_name = os.path.splitext(new_bam_name)[0]

    # Replace trailing _R1.
    if new_bam_name.endswith("_R1"):
        new_bam_name = new_bam_name[:-3]

    new_bam_name = new_bam_name + '.bam'
    print("New BAM name: %s" % new_bam_name)

    # Current bam is the only bam in the home directory
    current_bam_name = glob.glob("*.bam")[0]

    ##########
    # Moving #
    ##########

    printv("  [*] Moving BAM file...")
    printv("      - from: %s" % (current_bam_name))
    printv("      - to:   %s" % (new_bam_name))
    os.system("mv %s %s" % (current_bam_name, new_bam_name))

    ############
    # Indexing #
    ############

    printv("  [*] Indexing BAM file...", end="")
    with Timer() as t:
        os.system("chmod +x /sambamba; /sambamba index --nthreads $( nproc ) %s" %
                  (new_bam_name))
    printv("took %d seconds." % (t.interval))

    #############
    # Uploading #
    #############

    star_bam = dxpy.upload_local_file(new_bam_name)
    star_index = dxpy.upload_local_file(new_bam_name + ".bai")

    output = {}
    output["star_bam"] = dxpy.dxlink(star_bam)
    output["star_index"] = dxpy.dxlink(star_index)

    return output

dxpy.run()
