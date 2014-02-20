#! /usr/bin/env python

from pbcore.io.base import (getFileHandle,
                            WriterBase)

__author__ = 'bbowman@pacificbiosciences.com'


class AmpliconAnalysisRecord(object):
    """
    A record for representing consensus sequences generated by Amplicon Analysis
    """
    FASTA_DELIM = '>'
    COLUMNS = 60
    FASTQ_DELIM1 = '@'
    FASTQ_DELIM2 = '+'

    def __init__(self, name, sequence, quality=None):
        self._name = name
        self._sequence = sequence
        self._quality = quality

        try:
            name_parts = name.strip().split('NumReads')
            assert len(name_parts) == 2
            assert name_parts[1].isdigit()
            self._num_reads = int(name_parts[1])

            if quality is not None:
                assert len(self.sequence) == len(self.quality)
        except AssertionError:
            raise ValueError("Invalid AmpliconAnalysis sequence data")

    @property
    def name(self):
        return self._name

    @property
    def barcode(self):
        return self._name.split('_')[0][7:]

    @property
    def num_reads(self):
        return self._num_reads

    @property
    def sequence(self):
        return self._sequence

    @property
    def quality(self):
        if self._quality:
            return self._quality
        raise ValueError( "Record has no quality data" )

    @property
    def is_fasta(self):
        if self._quality:
            return False
        return True

    @property
    def is_fastq(self):
        return not self.is_fasta

    @classmethod
    def fastq_from_string(cls, s):
        try:
            lines = s.rstrip().split("\n")
            assert len(lines) == 4
            assert lines[0].startswith(cls.FASTQ_DELIM1)
            assert lines[2].startswith(cls.FASTQ_DELIM2)
            assert len(lines[1]) == len(lines[3])
            name = lines[0][1:]
            sequence = lines[1]
            quality = lines[3]
            return AmpliconAnalysisRecord(name, sequence, quality)
        except AssertionError:
            raise ValueError("Invalid AmpliconAnalysis fastq record")

    @classmethod
    def fasta_from_string(cls, s):
        try:
            lines = s.split("\n")
            assert len(lines) > 1
            assert lines[0].startswith('>')
            name = lines[0][1:]
            sequence = "".join(lines[1:])
            return AmpliconAnalysisRecord(name, sequence)
        except:
            raise ValueError("Invalid AmpliconAnalysis fasta record")

    def _slice(self, start, stop):
        if self.is_fasta:
            return AmpliconAnalysisRecord(self.name,
                                                  self.sequence[start:stop])
        elif self.is_fastq:
            return AmpliconAnalysisRecord(self.name,
                                                  self.sequence[start:stop],
                                                  self.quality[start:stop])

    def __len__(self):
        return len(self.sequence)

    def __getitem__(self, item):
        if isinstance(item, int):
            if item < 0 or item > len(self):
                raise IndexError("The index (%d) is out of range" % item)
            return self._sequence[item]
        elif isinstance(item, slice):
            start, stop, step = item.indices(len(self))
            if start >= stop:
                raise ValueError("Start index must be less than Stop index")
            return self._slice(start, stop)
        else:
            raise TypeError("Index must be Int or Slice")

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.name == other.name and
                    self.sequence == other.sequence and
                    self.quality == other.quality)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def as_fasta(self):
        return (">%s\n" % self.name) + wrap(self.sequence, self.COLUMNS)

    @property
    def as_fastq(self):
        if self.quality is None:
            raise ValueError("Record has no quality data")
        return "@%s\n%s\n+\n%s" % (self.name,
                                   self.sequence,
                                   self.quality)

    def __str__(self):
        if self.is_fasta:
            return self.as_fasta
        elif self.is_fastq:
            return self.as_fastq


class AmpliconAnalysisReader(object):
    """
    Read Amplicon Analysis sequence records from a file
    """
    def __init__(self, f):
        self.filename = f
        self.file = getFileHandle(f, "r")

    def close(self):
        """
        Close the underlying file
        """
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __iter__(self):
        """
        One-shot iteration support
        """
        while True:
            if self.filename.endswith('.fa') or self.filename.endswith('.fasta'):
                for part in self.file.read().split(">"):
                    if part.strip():
                        yield AmpliconAnalysisRecord.fasta_from_string(">" + part)
                break
            elif self.filename.endswith('.fq') or self.filename.endswith('.fastq'):
                lines = [next(self.file) for i in xrange(4)]
                yield AmpliconAnalysisRecord(lines[0][1:].strip(),
                                                     lines[1].strip(),
                                                     lines[3].strip())


class AmpliconAnalysisWriter(WriterBase):
    """
    Write Amplicon Analysis records out to a file
    """
    def write_record(self, record):
        assert isinstance(record, AmpliconAnalysisRecord)
        self.file.write(str(record))
        self.file.write("\n")

    def write_fasta(self, record):
        assert isinstance(record, AmpliconAnalysisRecord)
        self.file.write(record.as_fasta)
        self.file.write("\n")


def wrap(s, columns):
    return "\n".join(s[start:start+columns]
                     for start in xrange(0, len(s), columns))