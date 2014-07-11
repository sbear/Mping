from ping import Ping

p = Ping(destination='127.0.0.1',timeout=1000)
p.run(3)
print p.receive_count
p.run(4)
print p.receive_count
p.do()
p.do()
p.do()
print p.receive_count
