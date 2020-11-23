import tools.utils as utils
from configs import dfl, cfg

class NMEA:

    def __init__(self):
        self.new_sentence_flag = False
        self.checksum_flag = False
        self.checksum = []
        self.word = []
        self.sentence = []

    def verify_checksum(self, checksum, sentence):
        """Verifies the NMEA sentence integrity."""
        calculated_checksum = 0
        for char in ",".join(sentence):
            calculated_checksum ^= ord(char)
        if "{:02X}".format(calculated_checksum) != checksum:
            utils.log("NMEA invalid checksum calculated: {:02X} got: {}".format(calculated_checksum, checksum))
            return False
        return True

    def get_sentence(self, string, sentence):
        """Gets a single NMEA sentence, each sentence is a list of words itself."""
        for ascii in string:
            if ascii == "$":
                self.new_sentence_flag = True
                self.word = []
                self.sentence = []
                self.checksum = []
                self.checksum_flag = False
            elif ascii == ",":
                if self.new_sentence_flag:
                    self.sentence.append("".join(self.word))
                    self.word = []
            elif ascii == "*":
                if self.new_sentence_flag:
                    self.sentence.append("".join(self.word))
                    self.checksum_flag = True
            elif self.new_sentence_flag:
                if self.checksum_flag:
                    self.checksum.append(ascii)
                    if len(self.checksum) == 2:
                        if self.verify_checksum("".join(self.checksum), self.sentence):
                            self.sentence.insert(0,"$" + self.sentence[0])
                            self.sentence.pop(1)
                            self.sentence.insert(-1,self.sentence[-1]+ "*" + "".join(self.checksum))
                            self.sentence.pop(-1)
                            if sentence and self.sentence[0][-3:] == sentence:
                                return True
                else:
                    self.word.append(ascii)
