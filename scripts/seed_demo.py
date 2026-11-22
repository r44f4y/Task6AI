import argparse
from sqlalchemy.orm import Session
from backend.engine import seed
from backend.store import connect,write_lock
from synthetic_data.catalog import catalog

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--reset',action='store_true')
    args=parser.parse_args()
    fixtures=catalog()
    with Session(connect()) as session:
        write_lock(session)
        seed(session,fixtures,reset=args.reset)
        session.commit()
    print(f'{len(fixtures)} fictional scenarios available.')
