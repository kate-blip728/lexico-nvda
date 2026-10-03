from test_services import services

for word in ('océano', 'bueno'):
    print(services.lookup(word))
print(services.daily_word())
