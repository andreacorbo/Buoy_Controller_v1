import tools.utils as utils
import constants

class NMEA(object):

    def __init__(self, *args, **kwargs):
        self.new_sentence_flag = False
        self.checksum_flag = False
        self.checksum = ""
        self.word = ""
        self.sentence = []

    def verify_checksum(self, checksum, sentence):
        """Verifies the NMEA sentence integrity.

        Params:
            checksum(hex)
            sentence(list)
        """
        calculated_checksum = 0
        for char in ",".join(map(str, sentence)):
            calculated_checksum ^= ord(char)
        if "{:02X}".format(calculated_checksum) != checksum:
            utils.log("NMEA invalid checksum calculated: {:02X} got: {}".format(calculated_checksum, checksum))
            return False
        else:
            return True

    def _get_sentence(self, byte, sentence):
        """Gets a single NMEA sentence, each sentence is a list of words itself.

        Params:
            byte(int)
        """
        try:
            ascii = byte.decode("utf-8")
            if ascii == "$":
                self.new_sentence_flag = True
                self.word = ascii
                self.sentence = []
                self.checksum = ""
                self.checksum_flag = False
            elif ascii == ",":
                if self.new_sentence_flag:
                    self.sentence.append(self.word)
                    self.word = ""
            elif ascii == "*":
                if self.new_sentence_flag:
                    self.sentence.append(self.word + ascii)
                    self.checksum_flag = True
            elif self.new_sentence_flag:
                if self.checksum_flag:
                    self.checksum = self.checksum + ascii
                    if len(self.checksum) == 2:
                        print(",".join(self.sentence)[1:-1])
                        if self.verify_checksum(self.checksum, ",".join(self.sentence)[1:-1]):
                            self.sentence.insert(-1, self.sentence[-1] + self.checksum)
                            self.sentence.pop(-1)
                            if sentence and self.sentence[0][-3:] == sentence:
                                return True
                else:
                    self.word = self.word + ascii
        except UnicodeError:
            return False

    def get_sentence(self, byte, sentence):
        """Gets a single NMEA sentence, each sentence is a list of words itself.

        Params:
            byte(int)
        """
        try:
            ascii = byte.decode("utf-8")
            if ascii == "$":
                self.new_sentence_flag = True
                self.word = ""
                self.sentence = []
                self.checksum = ""
                self.checksum_flag = False
            elif ascii == ",":
                if self.new_sentence_flag:
                    self.sentence.append(self.word)
                    self.word = ""
            elif ascii == "*":
                if self.new_sentence_flag:
                    self.sentence.append(self.word)
                    self.checksum_flag = True
            elif self.new_sentence_flag:
                if self.checksum_flag:
                    self.checksum = self.checksum + ascii
                    if len(self.checksum) == 2:
                        if self.verify_checksum(self.checksum, self.sentence):
                            self.sentence.insert(0,"$" + self.sentence[0])
                            self.sentence.pop(1)
                            self.sentence.insert(-1,self.sentence[-1]+"*" + self.checksum)
                            self.sentence.pop(-2)
                            if sentence and self.sentence[0][-3:] == sentence:
                                return True
                else:
                    self.word = self.word + ascii
            return False
        except UnicodeError:
            pass
