import json
import argparse
from renewal import get_book_info, renew_book


def main():
	parser = argparse.ArgumentParser(description="Koha OPAC helper for Flutter integration")
	subparsers = parser.add_subparsers(dest="command", required=True)

	# get_book_info command
	p_info = subparsers.add_parser("get_book_info", help="Fetch current checkouts for a user")
	p_info.add_argument("userid", type=str, help="Koha user ID")
	p_info.add_argument("password", type=str, help="Koha password")

	# renew_book command
	p_renew = subparsers.add_parser("renew_book", help="Renew a specific item for a user")
	p_renew.add_argument("userid", type=str, help="Koha user ID")
	p_renew.add_argument("password", type=str, help="Koha password")
	p_renew.add_argument("item_id", type=int, help="Item ID to renew")

	args = parser.parse_args()

	try:
		if args.command == "get_book_info":
			result = get_book_info(args.userid, args.password)
		elif args.command == "renew_book":
			result = renew_book(args.userid, args.password, args.item_id)
		else:
			result = {"status": "error", "error": "Unknown command"}
	except Exception as e: 
		result = {"status": "error", "error": str(e)}

	# Print compact JSON for Flutter to parse
	print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
	main()



# python .\main.py get_book_info userid myPassword

# python .\main.py renew_book userid myPassword itemid