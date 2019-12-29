import * as React from 'react';
import {
  Text,
  View,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import { Constants } from 'expo';
import { Container, Content, Header, Icon, Item, Input } from 'native-base';

import FriendStream from './Friendstream';
import PopularStream from './PopularStream';

const { width, height } = Dimensions.get('window');
export default class Feeds extends React.Component {
  render() {
    return (
      <Container style={styles.container}>
        <Header
          searchBar
          rounded
          style={{
            backgroundColor: 'white',
            left: 0,
            right: 0,
            top: 0,
            zIndex: 100,
            alignItems: 'center',
          }}>
          <View style={{ flexDirection: 'row', flex: 1 }}>
            <Icon
              name="person"
              style={{ fontWeight: 'bold', fontSize: 40, color: 'black' }}
            />
            <Item style={{ backgroundColor: 'transparent' }}>
              <Icon
                name="ios-search"
                style={{
                  color: 'black',
                  fontSize: 30,
                  fontWeight: 'bold',
                }}
              />
              <Input placeholder="Search" placeholderTextColor="black" />
            </Item>
          </View>
        </Header>

        <View style={styles.container}>
          <ScrollView scrollEventThrottle={16}>
            <View style={{ flex: 1, backgroundColor: 'white' }}>
              <Text style={styles.paragraph}>Friends:</Text>
            </View>

            <View
              style={{
                height: 150,
                backgroundColor: '#fcfdfd',
                borderBottomColor: '#e6e6e6',
                borderBottomWidth: 1,
              }}>
              <ScrollView horizontal={true}>
                <TouchableOpacity style={styles.Streamingbutton}>
                  <Text
                    style={{
                      fontSize: 100,
                      fontWeight: 'bold',
                      color: 'white',
                    }}>
                    +
                  </Text>
                </TouchableOpacity>
                <FriendStream
                  source1={require('../assets/Profiles/pexels-photo-1239291.jpeg')}
                  source2={require('../assets/Profiles/pexels-photo-324658.jpeg')}
                />
                <FriendStream
                  source1={require('../assets/Profiles/pexels-photo-774909.jpeg')}
                />
                <FriendStream
                  source1={require('../assets/Profiles/pexels-photo-713312.jpeg')}
                />
                <FriendStream
                  source1={require('../assets/Profiles/pexels-photo-736716.jpeg')}
                  source2={require('../assets/Profiles/pexels-photo-220453.jpeg')}
                />
                <FriendStream
                  source1={require('../assets/Profiles/pexels-photo-539727.jpeg')}
                />
                <FriendStream
                  source1={require('../assets/Profiles/pexels-photo-935756.jpeg')}
                  source2={require('../assets/Profiles/pexels-photo-91227.jpeg')}
                />
              </ScrollView>
            </View>
            <View style={{ flex: 1, backgroundColor: 'white' }}>
              <Text style={styles.paragraph}>Popular:</Text>
              <View style={{ flexDirection: 'row', flex: 1, flexWrap: 'wrap' }}>
                <PopularStream
                  width={width}
                  source1={require('../assets/Profiles/pexels-photo-774095.jpeg')}
                  source2={require('../assets/Profiles/pexels-photo-756453.jpeg')}
                />
                <PopularStream
                  width={width}
                  source1={require('../assets/Profiles/pexels-photo-415829.jpeg')}
                  source2={require('../assets/Profiles/pexels-photo-462680.jpeg')}
                />
                <PopularStream
                  width={width}
                  source1={require('../assets/Profiles/pexels-photo-736716.jpeg')}
                />
                <PopularStream
                  width={width}
                  source1={require('../assets/Profiles/pexels-photo-614810.jpeg')}
                  source2={require('../assets/Profiles/pexels-photo-683381.jpeg')}
                />
                <PopularStream
                  width={width}
                  source1={require('../assets/Profiles/pexels-photo-818819.jpeg')}
                  source2={require('../assets/Profiles/pexels-photo-814052.jpeg')}
                />
              </View>
            </View>
          </ScrollView>
        </View>
      </Container>
    );
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: Constants.statusBarHeight,
    backgroundColor: 'white',
  },
  paragraph: {
    paddingHorzontal: 20,
    fontSize: 24,
    fontWeight: '600',
    color: 'black',
  },
  Streamingbutton: {
    height: 130,
    width: 90,
    marginTop: 10,
    marginBottom: 10,
    marginLeft: 10,
    backgroundColor: '#e6e6e6',
    overflow: 'hidden',
    borderColor: 'transparent',
    borderRadius: 20,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
