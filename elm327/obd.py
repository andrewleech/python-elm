################################################################################
# The MIT License (MIT)
#
# Copyright (c) 2014 Francisco Ruiz
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
################################################################################


_OBD_RESPONSE_NO_DATA = "NO DATA"

_OBD_RESPONSE_UNSUPPORTED_COMMAND = "?"

_INT_TO_HEX_WORD_FORMATTER = "{:0=2X}"

_INT_TO_HEX_WORD_FORMATTER_PRETTY = "{:0=#4x}"


class ELMError(Exception):
    pass


class ValueNotAvailableError(ELMError):
    pass


class OBDInterface(object):

    def __init__(self, connection):
        self._connection = connection

        self._unsupported_commands = []

        self.send_command("AT Z")
        self.send_command("AT E0")

    def send_command(self, data, read_delay=1):
        response = self._connection.send_command(data, read_delay)
        print(response.replace('\r', '\n').strip())
        return response

    def read_pcm_value(self, pcm_value_definition, read_delay=1):
        obd_command = pcm_value_definition.command
        if obd_command in self._unsupported_commands:
            raise ValueNotAvailableError()

        command_data = ' '.join(obd_command.to_hex_words())
        response_data = self.send_command(command_data, read_delay)
        response_data = response_data.split('\r')
        for response_d in response_data:
            try:
                response = self._make_pcm_value(response_d, pcm_value_definition)
                if response:
                    return response
            except ValueNotAvailableError:
                self._unsupported_commands.append(obd_command)
                raise

        return None

    @staticmethod
    def _make_pcm_value(response_raw, pcm_value_definition):
        if response_raw == _OBD_RESPONSE_NO_DATA:
            return None

        if response_raw == _OBD_RESPONSE_UNSUPPORTED_COMMAND:
            raise ValueNotAvailableError()

        response_words = _convert_raw_response_to_words(response_raw)

        print(response_words)
        if response_words[0] == 0x41 and response_words[1] == pcm_value_definition.command.pid:
            raw_data = tuple(response_words[2:])
            pcm_value = pcm_value_definition.parser(raw_data)
            return pcm_value

    def get_dtc(self, pending=False, read_delay=1):
        response_data = self.send_command("07" if pending else "03", read_delay)
        response_data = response_data.replace(' ', '').strip()
        response_data = response_data.split('\r')
        if response_data == _OBD_RESPONSE_NO_DATA:
            raise ValueNotAvailableError()
        codes = set()
        for response in response_data:
            if response.startswith('47' if pending else '43'):
                response = response[2:]
                while response:
                    code = response[0:4]
                    if code != '0000':
                        codes.add(code)
                    response = response[4:]
            else:
                print(response)
        return codes

    def clear_dtc(self, read_delay=1):
        response_data = self.send_command("04", read_delay)
        if response_data.startswith('44'):
            return True
        return False


def _convert_raw_response_to_words(raw_response):
    words_as_str = raw_response.split()
    words = [int(word, 16) for word in words_as_str]
    return words


class OBDCommand(object):

    def __init__(self, mode, pid):
        self.mode = mode
        self.pid = pid

    def to_hex_words(self, pretty=False):
        hex_words = (
            _convert_int_to_hex_word(self.mode, pretty=pretty),
            _convert_int_to_hex_word(self.pid, pretty=pretty),
            )
        return hex_words

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return hash((self.mode, self.pid))

    def __repr__(self):
        return "{}(mode={}, pid={})".format(
            self.__class__.__name__,
            *self.to_hex_words(True)
            )


def _convert_int_to_hex_word(i, pretty=False):
    if pretty:
        formatter = _INT_TO_HEX_WORD_FORMATTER_PRETTY
    else:
        formatter = _INT_TO_HEX_WORD_FORMATTER

    return formatter.format(i)
