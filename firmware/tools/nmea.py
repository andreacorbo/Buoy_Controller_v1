# The MIT License (MIT)
#
# Copyright (c) 2018 OGS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import tools.utils as utils
import constants

class NMEA(object):

    def __init__(self):
        self.new_sentence_flag = False
        self.checksum_flag = False
        self.checksum = ''
        self.checksum_verified = False
        self.word = ''
        self.sentence = []
        self.string = ''
        self.serial_string = ''

    def _verify_checksum(self, checksum, string):
        """Verifies the NMEA sentence integrity.

        Params:
            checksum(hex)
            string(str)
        """
        calculated_checksum = 0
        for char in string:
            calculated_checksum ^= ord(char)
        if "{:02X}".format(calculated_checksum) != checksum:
            self.checksum_verified = False
            utils.log_file("NMEA invalid checksum calculated: {:02X} got: {}".format(calculated_checksum, checksum), constants.LOG_LEVEL, new_line=True)
        else:
            self.checksum_verified = True

    def get_sentence(self, char_code):
        """Gets a single NMEA sentence, each sentence is a list of words itself.

        Params:
            char_code(int)
        """
        if char_code in range(32, 126):
            ascii_char = chr(char_code)
            if ascii_char == '$':
                self.new_sentence_flag = True
                self.word = ''
                self.sentence = []
                self.checksum = ''
                self.checksum_verified = False
                self.checksum_flag = False
            elif ascii_char == ',':
                if self.new_sentence_flag is True:
                    self.sentence.append(self.word)
                    self.word = ''
            elif ascii_char == '*':
                if self.new_sentence_flag is True:
                    self.sentence.append(self.word)
                    self.checksum_flag = True
            else:
                if self.new_sentence_flag is True:
                    if self.checksum_flag is True:
                        self.checksum = self.checksum + ascii_char
                        if len(self.checksum) == 2:
                            self.string = ','.join(map(str, self.sentence))
                            self._verify_checksum(self.checksum, self.string)
                            self.serial_string = "$" + self.string
                            self.new_sentence_flag = False
                    else:
                        self.word = self.word + ascii_char
