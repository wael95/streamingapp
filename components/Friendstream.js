import * as React from 'react';
import { Text, View, Image,TouchableOpacity } from 'react-native';

export default class FriendSream extends React.Component {
  render() {
    return (
      <TouchableOpacity
        style={{
          height: 130,
          width: 90,
          marginTop: 10,
          marginBottom: 10,
          marginLeft: 10,
          overflow: 'hidden',
          borderColor: 'transparent',
          borderRadius: 20,
          borderWidth: 1,
        }}>
        <View style={{ flex: 1 }}>
          <Image
            style={{
              flex: 1,
              height: null,
              width: null,
              resizeMode: 'cover',
            }}
            source={this.props.source1}
          />
        </View>
        {this.props.source2 ? <View style={{ flex: 1 }}>
          <Image
            style={{
              flex: 1,
              height: null,
              width: null,
              resizeMode: 'cover',
            }}
            source={this.props.source2}
          />
        </View> : <View/>}
      </TouchableOpacity>
    );
  }
}
