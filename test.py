import math
import serial
import time

# Panel controller protocol
#
# Panels respond to commands coming from either UART1 or UART2.
#
# Send command: [cmd_byte][panel 0 params][panel 1 params]...\r
# Receive response: [panel 0 response][panel 1 response]...\r
#
# E.g., the SET_STATUS command is 'S' and it takes four chars ('0' or '1') per panel.
# So the command for two panels, setting panel 0 to 1010 and panel 1 to 1110
# would be 'S10101110\r'.
#
# First command sent must be ENUMERATE. The response gives the two-byte version
# number of each panel, so you can divide by 2 to find out how many panels there are.
#
# The communication between panels is half-duplex so it is critical
# to wait for the terminating \r from the response before sending another
# command.
#
# Commands:
#
# ENUMERATE
# Send    E\r
# Receive [panel N-1 version][panel N-2 version]...[panel 0 version]\r
#         Each panel version is 2 bytes
#
# SET_LIGHTS
# Send    L[panel 0 red][panel 0 green][panel 0 blue][panel 1 red]...[panel N-1 blue]\r
# Receive [panel N-1 PIR][panel N-2 PIR]...[panel 0 PIR]\r
#         Each panel PIR is one byte: '1' is a high PIR input, '0' is low
#
# SET_STATUS
# Send    S[panel 0 status][panel 1 status]...[panel N-1 status]\r
#         Each panel status is [D5 stats][D6 state][D7 state][D8 state]
#         Each LED state is '1' for on or '0' for off
# Receive [unspecified]\r
#
# UPGRADE
# Send    U\r
# Receive [panel N-1 version]|[panel N-2 version]|[panel 0 version]|\r


ENUMERATE = 'E'
SET_STATUS = 'S'
SET_LIGHTS = 'L'
UPGRADE = 'U'

num_panels = 1

ser = serial.Serial("COM6", 230400, timeout=1)

def send_command(cmd_byte, params = ""):
	cmd_bytes = bytes(f"{cmd_byte}{params}\r", "utf-8")
	#print("> ", cmd_bytes)
	ser.write(cmd_bytes)
	response = ser.read_until(bytes("\r", "utf-8"))
	#print("< ", response)

	if len(response) == 0 or response[len(response)-1] != 13:
		print("TIMEOUT")
		exit()

	return response

def send_upgrade():
	old_timeout = ser.timeout
	ser.timeout = 30
	response = send_command(UPGRADE)
	ser.timeout = old_timeout
	response_str = response.decode("utf-8").strip()
	versions = response_str.split("|")[0:-1]
	return versions

def send_enumerate():
	response = send_command(ENUMERATE)
	global num_panels
	num_panels = (len(response) - 1) // 2
	response_str = response.decode("utf-8").strip()
	return [response_str[i:i+2] for i in reversed(range(0, len(response_str), 2))]

# statuses = ['1010', '0101', ...]
#
def send_set_status(statuses):
	return send_command(SET_STATUS, "".join(statuses))

# lights = [R0, G0, B0, R1, G1, B1, ...]
#
def send_set_lights(lights):
	response = send_command(SET_LIGHTS, "".join((f'{l:02x}' for l in lights)))
	return [b == ord('1') for b in reversed(response[0:-1])]

def wave(period, pos):
	return int(math.sin((pos / period) * 2*math.pi) * 127) + 128

def test():
	versions = send_enumerate()
	print(f"{num_panels} panel(s).")
	print(f"Versions: {versions}")
	versions = send_upgrade()
	print(f"Firmware: {versions}")
	period = 500
	i = 0
	while True:
		statuses = ['0'] * num_panels * 4
		statuses[int(i / 10) % len(statuses)] = '1'
		send_set_status(statuses)

		lights = [val for n in range(0, num_panels) for val in [wave(period, i), wave(period/3, i + n*50), wave(period*2, i + n*100)]]
		response = send_set_lights(lights)
		if response[0]:
			print(i)
		i += 1
		time.sleep(0.01)

if __name__ == "__main__":
	test()
