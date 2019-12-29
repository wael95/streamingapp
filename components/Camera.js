import * as React from 'react';
import { Text, View, StyleSheet } from 'react-native';
import { Constants, Camera, Permissions } from 'expo';
import {
  Button,
  Container,
  Header,
  Item,
  Icon,
  Input,
  Content,
} from 'native-base';
//import MaterialComunityIcons from 'react-native-vector-icons/MaterialComunityIcons';

export default class Camerav extends React.Component {
  constructor() {
    super();
    this.state = {
      hascameraperm: null,
      type: Camera.Constants.Type.front,
      recordingLogo: 'camera',
    };
  }
  async componentWillMount() {
    const Status = await Permissions.askAsync(Permissions.CAMERA);
    this.setState({ hascameraperm: Status.status === 'granted' });
  }

  _switchCamera = () => {
    if (this.state.type == Camera.Constants.Type.back) {
      this.setState({ type: Camera.Constants.Type.front });
    } else {
      this.setState({ type: Camera.Constants.Type.back });
    }
  };

  render() {
    const { hascameraperm } = this.state;
    if (hascameraperm == null) {
      return <View />;
    } else if (hascameraperm == false) {
      return (
        <View style={styles.container}>
          <Text style={styles.paragraph}>No Access To Camera </Text>
        </View>
      );
    } else {
      return (
        <View style={{ flex: 1 }}>
          <Camera
            style={{
              flex: 1,
              justifyContent: 'space-between',
              backgroundColor: '0.1',
            }}
            type={this.state.type}>
            <Header
              searchBar
              rounded
              style={{
                position: 'absolute',
                backgroundColor: 'transparent',
                left: 0,
                right: 0,
                top: 0,
                zIndex: 100,
                alignItems: 'center',
              }}>
              <View style={{ flexDirection: 'row', flex: 1 }}>
                <Icon name="person" style={{ fontSize: 40, color: 'white' }} />
                <Item style={{ backgroundColor: 'transparent' }}>
                  <Icon
                    name="ios-search"
                    style={{
                      color: 'white',
                      fontSize: 30,
                      fontWeight: 'bold',
                    }}
                  />
                  <Input placeholder="Search" placeholderTextColor="white" />
                </Item>
              </View>
            </Header>
            <View
              style={{
                flexDirection: 'row',
                justifyContent: 'space-between',
                padding: 15,
                alignItems: 'flex-end',
              }}>
              <Icon
                onPress={() => this._switchCamera()}
                name="ios-reverse-camera"
                style={{ fontSize: 40, color: 'white' }}
              />
              <Icon
                name={this.state.recordingLogo}
                onPress={() => {
                  this.setState({
                    recordingLogo:
                      this.state.recordingLogo === 'ios-camera'
                        ? 'camera'
                        : 'ios-camera',
                  });
                }}
                style={{ fontSize: 80, color: 'red' }}
              />
              <Icon name="ios-flash" style={{ fontSize: 40, color: 'white' }} />
            </View>
          </Camera>
        </View>
      );
    }
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: Constants.statusBarHeight,
  },
  paragraph: {
    margin: 24,
    fontSize: 30,
    fontWeight: 'bold',
    textAlign: 'center',
    color: 'black',
  },
});
