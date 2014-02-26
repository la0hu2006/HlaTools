#! /usr/bin/env python

import logging

from pbcore.io.FastaIO import FastaReader
from pbcore.io.FastqIO import FastqReader, FastqWriter
from pbhla.filenames import get_file_type
from pbhla.io.BlasrIO import BlasrReader
from pbhla.utilities.reverse_complement import reverse_complement
from pbhla.fasta.utils import write_fasta
from pbhla.external.utils import get_alignment_file
from pbhla.utils import check_output_file, valid_file

log = logging.getLogger()

def orient_sequences( input_file, reference_file=None, alignment_file=None, output_file=None ):
    """
    Reorient a fasta file so all sequences are in the same direction as their reference
    """
    log.info("Reorienting all sequences in %s to the direction of their reference" % input_file)
    # Set the output file and type
    output_file = output_file or _get_output_file( input_file )
    output_type = _get_output_type( output_file )
    if valid_file( output_file ):
        log.info("Found existing output file %s, skipping orientation step" % output_file)
        return output_file
    # Check the input files, and align the input file if needed
    alignment_file = get_alignment_file( input_file, reference_file, alignment_file )
    reversed_seqs = _identify_reversed_sequences( alignment_file )
    log.info("Identified %s sequences needing Reverse Complementation" % len(reversed_seqs))
    input_records = _parse_input_records( input_file )
    reversed_records = _reverse_records( input_records, reversed_seqs )
    log.info("Writing out sequences to %s" % output_file)
    _write_output( reversed_records, output_file, output_type )
    return output_file

def _get_output_file( input_file ):
    """
    Get the output file, either as provided or from the input filename
    """
    basename = '.'.join( input_file.split('.')[:-1] ) 
    input_type = get_file_type( input_file )
    return '%s.oriented.%s' % (basename, input_type)

def _get_output_type( output_file ):
    """
    Get the output filetype and confirm the format is valid
    """
    output_type = get_file_type( output_file )
    if output_type in ['fasta', 'fastq']:
        return output_type
    else:
        msg = "Output file must be either Fasta or Fastq format"
        log.error( msg )
        raise TypeError( msg )

def _identify_reversed_sequences( blasr_file ):
    """
    Identify hits where the query and reference have difference orientations
    """
    reversed_seqs = []
    for record in BlasrReader( blasr_file ):
        if record.qstrand != record.tstrand:
            reversed_seqs.append( record.qname )
    return set(reversed_seqs)

def _parse_input_records( input_file ):
    """
    Parse the input sequence records with the appropriate pbcore Reader
    """
    input_type = get_file_type( input_file )
    if input_type == 'fasta':
        return list( FastaReader( input_file ))
    elif input_type == 'fastq':
        return list( FastqReader( input_file ))
    else:
        msg = 'Input file must be either Fasta or Fastq'
        log.error( msg )
        raise TypeError( msg )

def _reverse_records( records, reversed_seqs ):
    """
    Reverse-comeplement the records specified in a list
    """
    reversed_records = []
    for record in records:
        name = record.name.split()[0]
        if name in reversed_seqs:
            record = reverse_complement( record )
        reversed_records.append( record )
    return reversed_records

def _write_output( records, output_file, output_type ):
    """
    Write the records out to file
    """
    if output_type == 'fasta':
        write_fasta( records, output_file )
    else:
        with FastqWriter( output_file ) as writer:
            for record in records:
                writer.writeRecord( record )
    check_output_file( output_file )
    return output_file

if __name__ == '__main__':
    import sys
    logging.basicConfig( level=logging.INFO )

    input_file = sys.argv[1]
    reference_file = sys.argv[2]

    orient_sequences( input_file, reference_file=reference_file )
